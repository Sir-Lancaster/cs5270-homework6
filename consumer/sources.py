from abc import ABC 
from abc import abstractmethod

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
