import boto3
from moto import mock_aws
from sources import S3RequestSource, SQSRequestSource

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
    assert source.get_next_request() == (request_text, "request-1")
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    assert response.get("Contents", []) == []


@mock_aws
def test_get_next_request_processes_only_one_request_per_call():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=BUCKET_NAME)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="request-2",
        Body=b'{"widgetId": "456"}',
    )
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="request-1",
        Body=b'{"widgetId": "123"}',
    )

    source = S3RequestSource(s3, BUCKET_NAME)
    first_request = source.get_next_request()
    assert first_request == ('{"widgetId": "123"}', "request-1")
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    remaining_objects = response.get("Contents", [])
    assert len(remaining_objects) == 1

@mock_aws
def test_get_next_request_returns_none_on_empty_queue():
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = sqs.create_queue(QueueName="test-queue")["QueueUrl"]
    source = SQSRequestSource(sqs, queue_url)

    assert source.get_next_request() is None


@mock_aws
def test_sqs_returns_body_and_handle():
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = sqs.create_queue(QueueName="test-queue")["QueueUrl"]
    body = '{"widgetId": "1"}'
    sqs.send_message(QueueUrl=queue_url, MessageBody=body)
    source = SQSRequestSource(sqs, queue_url)

    result = source.get_next_request()

    assert isinstance(result, tuple)
    assert result[0] == body
    assert isinstance(result[1], str)
    assert result[1]


@mock_aws
def test_handles_a_batch_one_at_a_time():
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = sqs.create_queue(QueueName="test-queue")["QueueUrl"]
    bodies = [
        '{"widgetId": "1"}',
        '{"widgetId": "2"}',
        '{"widgetId": "3"}',
    ]
    for body in bodies:
        sqs.send_message(QueueUrl=queue_url, MessageBody=body)

    source = SQSRequestSource(sqs, queue_url)
    results = [source.get_next_request() for _ in range(3)]

    assert {body for body, _ in results} == set(bodies)
    assert source.get_next_request() is None


@mock_aws
def test_complete_deletes_the_message():
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = sqs.create_queue(
        QueueName="test-queue",
        Attributes={"VisibilityTimeout": "0"}
    )["QueueUrl"]
    sqs.send_message(QueueUrl=queue_url, MessageBody='{"widgetId": "1"}')
    source = SQSRequestSource(sqs, queue_url)

    _, handle = source.get_next_request()
    source.complete(handle)

    response = sqs.receive_message(
        QueueUrl=queue_url
    )
    assert "Messages" not in response


@mock_aws
def test_no_complete_means_its_not_deleted():
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = sqs.create_queue(
        QueueName="test-queue",
        Attributes={"VisibilityTimeout": "0"}
    )["QueueUrl"]
    sqs.send_message(QueueUrl=queue_url, MessageBody='{"widgetId": "1"}')
    source = SQSRequestSource(sqs, queue_url)

    source.get_next_request()

    response = sqs.receive_message(
        QueueUrl=queue_url
    )
    assert "Messages" in response