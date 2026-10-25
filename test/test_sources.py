import boto3
from moto import mock_aws
from sources import S3RequestSource

BUCKET_NAME = "request-bucket"


@mock_aws
def test_get_next_request_returns_none_for_empty_bucket():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)
    source = S3RequestSource(s3, BUCKET_NAME)
    assert source.get_next_request() is None


@mock_aws
def test_get_next_request_reads_and_deletes_request():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)
    request_text = '{"type": "create", "widgetId": "123"}'
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="request-1",
        Body=request_text.encode("utf-8"),
    )
    source = S3RequestSource(s3, BUCKET_NAME)
    assert source.get_next_request() == request_text
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    assert response.get("Contents", []) == []


@mock_aws
def test_get_next_request_processes_only_one_request_per_call():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="request-1",
        Body=b'{"widgetId": "123"}',
    )
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="request-2",
        Body=b'{"widgetId": "456"}',
    )

    source = S3RequestSource(s3, BUCKET_NAME)
    first_request = source.get_next_request()
    assert first_request in (
        '{"widgetId": "123"}',
        '{"widgetId": "456"}',
    )
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    remaining_objects = response.get("Contents", [])
    assert len(remaining_objects) == 1