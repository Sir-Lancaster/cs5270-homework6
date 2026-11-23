import argparse
import boto3
import logging
import time

# module imports
from parsing import parse_request
from sources import S3RequestSource
from sources import SQSRequestSource
from storage import S3WidgetStorage
from storage import DynamoWidgetStorage

def main():
    """Driver function of the consumer program. Parses command line arguments, 
    configures logging settings, polls the queue and processes requests."""

    arg = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("consumer.log"),
            logging.StreamHandler(),
        ],
    )

    s3_client=boto3.client("s3")

    # Choose storage
    if arg.storage == "s3":
        storage = S3WidgetStorage(s3_client, arg.widget_bucket)
    else: 
        dynamo_table = boto3.resource("dynamodb").Table(arg.table)
        storage = DynamoWidgetStorage(dynamo_table)

    # Choose source
    if arg.queue is not None:
        sqs_client = boto3.client("sqs")
        queue_url = sqs_client.get_queue_url(QueueName=arg.queue)["QueueUrl"]
        source = SQSRequestSource(sqs_client, queue_url)
    else:
        source = S3RequestSource(s3_client, arg.request_bucket)
    
    poll(source, storage, arg.max_empty_polls)

def poll(source, storage, max_empty_polls):
    """Gets the next request from the source. If poll returns empty the function accumulates a count, 
    after the accumulated sequential empty polls reaches the max_empty_polls, function returns."""

    empty_polls = 0
    while empty_polls < max_empty_polls:
        try:
            result = source.get_next_request()
            if result is not None:
                request_raw, request_handle = result
                empty_polls = 0
                request = parse_request(request_raw)
                if request is None:
                    source.complete(request_handle)
                    continue
                processRequest(request, storage)
                source.complete(request_handle)
            else: 
                empty_polls += 1
                time.sleep(0.1) # 100 milisecnds
        except Exception: 
            empty_polls += 1
            time.sleep(0.1)
            logging.exception("Error handling request.")

def processRequest(request, storage):
    """Uses switch/case block to handle create, update, and delete requests."""

    match request['type']:
        case "create":
            storage.create(request)
        
        case "update":
            storage.update(request)
        
        case "delete":
            storage.delete(request)
            
        case _:
            logging.warning(f"bad request type on widget {request['widgetId']}")

def parse_args(argv=None):
    """Parses command line arguments to determine storage location, source, request bucket, 
    widget bucket, table, and maximum empty polls. returns the arguments."""

    parser = argparse.ArgumentParser(description="Widget request consumer")
    source_group = parser.add_mutually_exclusive_group(required=True)

    parser.add_argument("--storage", choices=["s3", "dynamo"], required=True, help="where to store widgets")
    source_group.add_argument("--request_bucket", help="name of the bucket that producer stores requests in.")
    source_group.add_argument("--queue", help="Name of the sqs queue to read requests from.")
    parser.add_argument("--widget_bucket", required=False, help="name of the bucket to store widgets at in s3")
    parser.add_argument("--table", required=False, default="widgets", help="name of the table where widgets are stored in DynamoDB")
    parser.add_argument("--max_empty_polls", required=False, type=int, default=100, help="Number of empty polls before exiting")

    args = parser.parse_args(argv)
    if args.storage == "s3" and args.widget_bucket == None:
        parser.error("Missing s3 widget bucket.")
    return args

if __name__ == "__main__": main()