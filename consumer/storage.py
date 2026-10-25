
from abc import ABC
from abc import abstractmethod
import json
import logging


class WidgetStorage(ABC):
    @abstractmethod
    def create(self, widgets):
        ...

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
        logging.info("Created widget %s in S3 bucket %s", widget["widgetId"], self.bucket_name)


class DynamoWidgetStorage(WidgetStorage):
    def __init__(self, dynamo_table):
        self.dynamo_table = dynamo_table

    def to_item(self, widget):
        item = {
            "id": widget["widgetId"],
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
        logging.info("Created widget %s in DynamoDB table %s", widget["widgetId"], self.dynamo_table.name)