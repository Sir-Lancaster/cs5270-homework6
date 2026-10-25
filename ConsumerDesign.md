# Consumer Design
Processes JSON objects as requests to create, update, or deleteWidgest. 

## Requirements
1. Store widgets in either s3 bucket 3 or dynamoBD table. 
    - Specify command line arguments to determine which.
2. Read requests 1 at a time, not all at once. 
    - Multiple consumers should be able to run at a time.
3. When a request is read, process in this workflow:
    - read object from bucket 2
    - delete from bucket 2
    - process request --> store in either s3 or Dynamo
    - read next object in bucket 2
4. Consumer needs to use a JSON parsing library to read requests. 
    - Schema is downloaded, use it as a template.
    - Create request is the only one for homework six.
5. When storing into a bucket, serialize the widget into a JSON string, and store the string.
    - Store with this key pattern: widgets/{owner}/{widget id}
6. When storing in dynamodb, all properties listed in the `otherAttributes` need to be stored as attributes in the object, not as a map or list.

---

## Design

```python
class WidgetStorage(ABC):
    @abstractmethod
    def create(self, widget): 
        ...
    # HW7 will add update() and delete()


class S3WidgetStorage(WidgetStorage):
    def __init__(self, s3_client, bucket_name):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def create(self, widget):
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f"widgets/{widget['owner'].lower().replace(' ', '-')}/{widget['widgetId']}",
            Body=json.dumps(widget),
        )


class DynamoWidgetStorage(WidgetStorage):
    def __init__(self, dynamo_table):
        self.dynamo_table = dynamo_table

    def to_item(self, widget):
        item = {
            "widget_id": widget["widgetId"],
            "owner": widget["owner"],
        }

        for field in ("label", "description"):
            if field in widget:
                item[field] = widget[field]

        for attribute in widget.get("otherAttributes", []):
            item[attribute["name"]] = attribute["value"]

        return item

    def create(self, widget):
        item = self.to_item(widget)
        self.dynamo_table.put_item(Item=item)

class RequestSource(ABC):
    @abstractmethod
    def get_next_request(self):
        ...

class S3RequestSource(RequestSource):
    def __init__(self, s3_client, bucket_name):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def get_next_request(self):
        resp = self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
        contents = resp.get("Contents", [])
        key = contents[0]["Key"] if contents else None
        if key is None:
            return None
        obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        text = obj["Body"].read().decode("utf-8")
        self.s3_client.delete_object(Key=key, Bucket=self.bucket_name)
        return text

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

def parse_request(text):
    try:
        request = json.loads(text)
    except json.JSONDecodeError as e:
        logging.warning("Skipping request: invalid JSON (%s)", e)
        return None

    if not isinstance(request, dict):
        logging.warning("Skipping request: not a JSON object")
        return None

    if not request.get('type') in ("create", "update", "delete"):
        logging.warning("Skipping request: incorrect type")
        return None

    if "owner" not in request or "widgetId" not in request:
        logging.warning("Skipping request: missing owner or widget id")
        return None
    return request

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
```