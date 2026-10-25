import argparse
import boto3
import logging
import time

# module imports
from parsing import parse_request
from sources import S3RequestSource
from storage import S3WidgetStorage
from storage import DynamoWidgetStorage

def main():
    arg = parse_args()

    logging.basicConfig(
        filename="consumer.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    s3_client=boto3.client("s3")

    if arg.storage == "s3":
        storage = S3WidgetStorage(s3_client, arg.widget_bucket)
    else: 
        dynamo_table = boto3.resource("dynamodb").Table(arg.table)
        storage = DynamoWidgetStorage(dynamo_table)

    source = S3RequestSource(s3_client, arg.request_bucket)
    poll(source, storage, arg.max_empty_polls)

def poll(source, storage, max_empty_polls):
    empty_polls = 0
    while empty_polls < max_empty_polls:
        request_raw = source.get_next_request()
        if request_raw is not None:
            empty_polls = 0
            request = parse_request(request_raw)
            if request is None:
                continue
            processRequest(request, storage)
        else: 
            empty_polls += 1
            time.sleep(0.1) # 100 milisecnds

def processRequest(request, storage):
    match request['type']:
        case "create":
            storage.create(request)
        
        case "update":
            pass
        
        case "delete":
            pass
        case _:
            logging.warning(f"bad request type on widget {request['widgetId']}")

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Widget request consumer")
    parser.add_argument("--storage", choices=["s3", "dynamo"], required=True, help="where to store widgets")
    parser.add_argument("--request_bucket", required=True, help="name of the bucket that producer stores requests in.")
    parser.add_argument("--widget_bucket", required=False, help="name of the bucket to store widgets at in s3")
    parser.add_argument("--table", required=False, default="widgets", help="name of the table where widgets are stored in DynamoDB")
    parser.add_argument("--max_empty_polls", required=False, type=int, default=100, help="Number of empty polls before exiting")

    args = parser.parse_args(argv)
    if args.storage == "s3" and args.widget_bucket == None:
        parser.error("Missing s3 widget bucket.")
    return args

if __name__ == "__main__": main()