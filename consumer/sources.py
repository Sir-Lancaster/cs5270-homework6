from abc import ABC 
from abc import abstractmethod

class RequestSource(ABC):
    @abstractmethod
    def get_next_request(self):
        """Returns (text, handle) for the next request, or none if none available."""
        ...

    @abstractmethod
    def complete(self, handle):
        """Marks the request identified by handle as finished."""
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
        return text, key

    def complete(self, handle):
        """S3 requests are deleted when they're read. no-op."""
        pass

class SQSRequestSource(RequestSource):
    def __init__(self, sqs_client, queue_url):
        self.sqs_client = sqs_client
        self.queue_url = queue_url
        self.cache = []

    def get_next_request(self):
        """Returns the next cached message, receiving a new batch of up to 10 when the cache is empty."""
        if not self.cache:
            resp = self.sqs_client.receive_message(QueueUrl=self.queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=10)
            self.cache.extend(resp.get("Messages", []))
        if not self.cache:
            return None
        
        message = self.cache.pop(0)

        return (message["Body"], message["ReceiptHandle"])

    def complete(self, handle):
        self.sqs_client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=handle)