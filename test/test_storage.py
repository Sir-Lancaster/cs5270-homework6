import json
import boto3
import pytest
from unittest.mock import Mock
from moto import mock_aws
from botocore.exceptions import ClientError
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

@pytest.fixture
def s3_storage():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-widgets")
        yield S3WidgetStorage(s3, "test-widgets"), s3

def test_s3_apply_update_applies_all_rules():
    storage = S3WidgetStorage(Mock(), "test-bucket")
    widget = {
        "widgetId": "1", 
        "owner": "Jane Doe", 
        "label": "Old", 
        "description": "Keep me", 
        "otherAttributes": [
            {"name": "color", "value": "red"}, 
            {"name": "size", "value": "5"}
        ]
    }
    request = {
        "widgetId": "1", "owner": "Jane Doe",
        "label": "New",
        "description": None,
        "otherAttributes": [
            {"name": "color", "value": "blue"},
            {"name": "size", "value": ""},
            {"name": "width", "value": "10"},
            {"name": "id", "value": "hacked"}
        ]
    }

    result = storage.apply_update(widget, request)

    assert result == {
        "widgetId": "1", "owner": "Jane Doe",
        "label": "New",
        "description": "Keep me",
        "otherAttributes": [
            {"name": "color", "value": "blue"},
            {"name": "width", "value": "10"},
        ]
    }

def test_s3_update_changes_existing_widget(s3_storage):
    storage, s3 = s3_storage
    storage.create({"type": "create", "widgetId": "1", "owner": "Jane Doe", "label": "Old"})

    request = {"type": "update", "widgetId": "1", "owner": "Jane Doe", "label": "New"}
    storage.update(request)

    obj = s3.get_object(Bucket="test-widgets", Key=storage.make_key(request))
    widget = json.loads(obj["Body"].read())
    assert widget["label"] == "New"

def test_s3_update_doesnt_create_new_widget(s3_storage, caplog):
    storage, s3 = s3_storage

    request = {"type": "update", "widgetId": "1", "owner": "Jane Doe", "label": "New"}
    storage.update(request)
    assert "Contents" not in s3.list_objects_v2(Bucket="test-widgets")
    assert "not found" in caplog.text

def test_s3_delete_removes_existing_widget(s3_storage):
    storage, s3 = s3_storage
    storage.create({"type": "create", "widgetId": "1", "owner": "Jane Doe", "label": "Old"})

    request = {"type": "delete", "widgetId": "1", "owner": "Jane Doe"}
    storage.delete(request)
    with pytest.raises(ClientError):
        s3.head_object(Bucket="test-widgets", Key=storage.make_key(request))

def test_s3_delete_doesnt_raise_on_missing_widget(s3_storage, caplog):
    storage, s3 = s3_storage
    request = {"type": "delete", "widgetId": "1", "owner": "Jane Doe"}
    storage.delete(request)
    assert "not found" in caplog.text

def test_dynamo_to_item_converts_widget_fields():
    table = Mock()
    storage = DynamoWidgetStorage(table)
    item = storage.to_item(WIDGET)

    assert item == {
        "id": "12345",
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
        "id": "12345",
        "owner": "Jane Doe",
    }

def test_dynamo_create_puts_flattened_item_in_table():
    table = Mock()
    storage = DynamoWidgetStorage(table)
    storage.create(WIDGET)

    table.put_item.assert_called_once_with(
        Item={
            "id": "12345",
            "owner": "Jane Doe",
            "label": "Temperature",
            "description": "Displays temperature",
            "units": "celsius",
            "location": "lab",
        }
    )

@pytest.fixture
def dynamo_table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="widgets",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table

def test_dynamo_apply_update_applies_all_rules():
    storage = DynamoWidgetStorage(Mock())
    item = {"id": "1", "owner": "Jane Doe", "label": "Old",
            "description": "Keep me", "color": "red", "size": "5"}
    request = {
        "widgetId": "1", "owner": "Jane Doe",
        "label": "New",
        "description": None,
        "otherAttributes": [
            {"name": "color", "value": "blue"},
            {"name": "size", "value": ""},
            {"name": "width", "value": "10"},
            {"name": "id", "value": "hacked"},
        ],
    }

    result = storage.apply_update(item, request)

    assert result == {
        "id": "1",
        "owner": "Jane Doe", 
        "label": "New", 
        "description": "Keep me", 
        "color": "blue",
        "width": "10"
    }

def test_dynamo_update_changes_existing_widget(dynamo_table):
    dynamo_table.put_item(Item={"id": "1", "owner": "Jane Doe", "label": "Old"})
    storage = DynamoWidgetStorage(dynamo_table)

    storage.update({"type": "update", "widgetId": "1", "owner": "Jane Doe", "label": "New"})

    item = dynamo_table.get_item(Key={"id": "1"})["Item"]
    assert item["label"] == "New"

def test_dynamo_update_Doesnt_create_widget_when_widget_not_found(dynamo_table):
    dynamo_table.put_item(Item={"id": "1", "owner": "Jane Doe", "label": "Old"})
    storage = DynamoWidgetStorage(dynamo_table)

    storage.update({"type": "update", "widgetId": "2", "owner": "John Doe", "label": "New"})

    assert "Item" not in dynamo_table.get_item(Key={"id": "2"})

def test_dynamo_delete_deletes_a_widget(dynamo_table):
    dynamo_table.put_item(Item={"id": "1", "owner": "Jane Doe", "label": "Old"})
    storage = DynamoWidgetStorage(dynamo_table)

    storage.delete({"type": "delete", "widgetId": "1", "owner": "Jane Doe"})

    assert "Item" not in dynamo_table.get_item(Key={"id": "1"})


def test_dynamo_delete_error_isnt_raised_on_missing_key(dynamo_table, caplog):
    storage = DynamoWidgetStorage(dynamo_table)
    storage.delete({"type": "delete", "widgetId": "1", "owner": "Jane Doe"})
    assert "not found" in caplog.text