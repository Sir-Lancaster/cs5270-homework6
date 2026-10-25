import json
from unittest.mock import Mock
import boto3
from moto import mock_aws
from storage import DynamoWidgetStorage, S3WidgetStorage

WIDGET = {
    "widgetId": "12345",
    "owner": "Jane Doe",
    "label": "Temperature",
    "description": "Displays temperature",
    "otherAttributes": [
        {"name": "units", "value": "celsius"},
        {"name": "location", "value": "lab"},
    ],
}

@mock_aws
def test_s3_create_stores_widget_under_expected_key():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-widgets")

    storage = S3WidgetStorage(s3, "test-widgets")
    storage.create(WIDGET)
    response = s3.get_object(
        Bucket="test-widgets",
        Key="widgets/jane-doe/12345",
    )

    stored_widget = json.loads(response["Body"].read().decode("utf-8"))

    assert stored_widget == WIDGET

def test_dynamo_to_item_converts_widget_fields():
    table = Mock()
    storage = DynamoWidgetStorage(table)
    item = storage.to_item(WIDGET)

    assert item == {
        "widget_id": "12345",
        "owner": "Jane Doe",
        "label": "Temperature",
        "description": "Displays temperature",
        "units": "celsius",
        "location": "lab",
    }

def test_dynamo_to_item_omits_optional_fields_when_missing():
    table = Mock()
    storage = DynamoWidgetStorage(table)
    widget = {
        "widgetId": "12345",
        "owner": "Jane Doe",
    }

    assert storage.to_item(widget) == {
        "widget_id": "12345",
        "owner": "Jane Doe",
    }

def test_dynamo_create_puts_flattened_item_in_table():
    table = Mock()
    storage = DynamoWidgetStorage(table)
    storage.create(WIDGET)

    table.put_item.assert_called_once_with(
        Item={
            "widget_id": "12345",
            "owner": "Jane Doe",
            "label": "Temperature",
            "description": "Displays temperature",
            "units": "celsius",
            "location": "lab",
        }
    )