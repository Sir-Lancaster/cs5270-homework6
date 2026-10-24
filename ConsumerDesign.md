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

    # HW7 will add update() and delete()


class S3WidgetStorage(WidgetStorage):
    def __init__(self, s3_client, bucket_name):
        # remember these on self

    def create(self, widget):
        # key  = build widgets/{owner}/{id}   (owner: lowercase, spaces -> dashes)
        # body = widget as a JSON string
        # upload body to bucket under key


class DynamoWidgetStorage(WidgetStorage):
    def __init__(self, dynamo_table):
        # remember it on self

    def create(self, widget):
        # item = widget's fields + each otherAttribute as its own key
        # put item into table

class S3RequestSource(RequestSource):
    def __init__(self, s3_client, bucket_name):

    def get_next_request(self):


def main():
    arg = parse_args()
    if arg.storage == "s3":
        storage = S3WidgetStorage(s3_client, arg.widget_bucket)
    else: 
        storage = DynamoWidgetStorage(dynamo_table)
    source = S3RequestSource(s3_client, arg.request_bucket)
    poll(source, storage, arg.max_empty_polls = 10)

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



def processRequest(object request, WidgetStorage storage):
    switch request.type:
        case request.type == "create":
            storage.create(a)
        
        case request.type == "update":
            pass
        
        case request.type == "delete":
            pass

```

