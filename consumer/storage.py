
from abc import ABC
from abc import abstractmethod
from botocore.exceptions import ClientError
import json
import logging


class WidgetStorage(ABC):
    @abstractmethod
    def create(self, widgets):
        ...

    @abstractmethod
    def delete(self, widgets):
        ...

    @abstractmethod
    def update(self, request):
        ...

    @abstractmethod
    def apply_update(self, item, request):
        ...

class S3WidgetStorage(WidgetStorage):
    def __init__(self, s3_client, bucket_name):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def make_key(self, request):
        return f"widgets/{request['owner'].lower().replace(' ', '-')}/{request['widgetId']}"

    def find_attribute(self, attributes, name):
        for index, attr in enumerate(attributes):
            if attr["name"] == name:
                return index
        return None

    def create(self, widget):
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self.make_key(widget),
            Body=json.dumps(widget),
        )
        logging.info("Created widget %s in S3 bucket %s", widget["widgetId"], self.bucket_name)

    def delete(self, request):
        """Removes widget. If it doesn't exist, log warning and move on."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=self.make_key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logging.warning("Widget %s not found in bucket %s", request["widgetId"], self.bucket_name)
                return
            else: 
                raise
            
        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=self.make_key(request) 
            )
        logging.info("Deleted widget %s from s3 bucket %s", request["widgetId"], self.bucket_name)

    def update(self, request):
        """Applies an update request to an existing widget; logs a warning if the widget does not exist."""
        try: 
            obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=self.make_key(request))
        except ClientError as e: 
            if e.response["Error"]["Code"] == "NoSuchKey":
                logging.warning("Key %s was not found in s3 bucket %s", request["widgetId"], self.bucket_name)
                return
            else: 
                raise

        widget = json.loads(obj["Body"].read().decode("utf-8"))
        updated = self.apply_update(widget, request)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self.make_key(request),
            Body=json.dumps(updated)
        )
        logging.info("Updated widget %s in bucket %s", request["widgetId"], self.bucket_name)

    def apply_update(self, widget, request):
        """change the attributes mentioned in request. 
        If attribute missing or null, leave it unchanged. 
        If attribute is an empty string, remove it from the widget."""

        for field in ("label", "description"):
            if field not in request or request[field] is None: 
                continue
            elif request[field] == "":
                widget.pop(field, None)
            else: 
                widget[field] = request[field]

        attributes = widget.setdefault("otherAttributes", [])
        for attribute in request.get("otherAttributes", []):
            name = attribute["name"]
            value = attribute.get("value")
            if name == "id" or name == "owner":
                continue

            index = self.find_attribute(attributes, name)
            if value is None:
                continue
            elif value == "":
                if index is not None:
                    attributes.pop(index)
            else: 
                if index is not None:
                    attributes[index]["value"] = value
                else: 
                    attributes.append({"name": name, "value": value})

        return widget


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

    def delete(self, request):
        """Removes widget. If it doesn't exist, log warning and move on."""
        response = self.dynamo_table.delete_item(
            Key={"id": request["widgetId"]},
            ReturnValues="ALL_OLD"
        )
        if response.get("Attributes") is None:
            logging.warning("Unable to delete widget %s; widget not found in table %s", request["widgetId"], self.dynamo_table.name)
        else: 
            logging.info("Widget %s deleted from table %s", request["widgetId"], self.dynamo_table.name)

    def update(self, request):
        """Applies an update request to an existing widget; logs a warning if the widget does not exist."""
        response = self.dynamo_table.get_item(Key={"id": request["widgetId"]})
        item = response.get("Item")
        if item is None:
            logging.warning("failed to find widget %s in DynamoDB table %s", request["widgetId"], self.dynamo_table.name)
            return
        
        updated = self.apply_update(item, request)
        self.dynamo_table.put_item(Item=updated)
        logging.info("Updated widget %s in DynamoDB table %s", request["widgetId"], self.dynamo_table.name)

    def apply_update(self, item, request):
        """change the attributes mentioned in request. 
        If attribute missing or null, leave it unchanged. 
        If attribute is an empty string, remove it from the widget."""
     
        for field in ("label", "description"):
            if field not in request or request[field] is None: 
                continue
            elif request[field] == "":
                item.pop(field, None)
            else: 
                item[field] = request[field]

        for attribute in request.get("otherAttributes", []):
            name = attribute["name"]
            value = attribute.get("value")
            if name == "id" or name == "owner":
                continue
            elif value is None:
                continue
            elif value == "":
                item.pop(name, None)
            else:
                item[name] = value
        
        return item