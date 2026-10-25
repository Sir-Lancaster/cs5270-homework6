from unittest.mock import Mock, patch
import pytest
from consumer import parse_args, poll, processRequest

REQUEST = {
    "type": "create",
    "owner": "Jane Doe",
    "widgetId": "widget-123",
}

def test_process_request_dispatches_create_to_storage():
    storage = Mock()
    processRequest(REQUEST, storage)
    storage.create.assert_called_once_with(REQUEST)

@pytest.mark.parametrize("request_type", ["update", "delete"])
def test_process_request_does_not_store_unimplemented_operations(request_type):
    storage = Mock()
    request = {
        **REQUEST,
        "type": request_type,
    }

    processRequest(request, storage)

    storage.create.assert_not_called()
    storage.update.assert_not_called()
    storage.delete.assert_not_called()

def test_poll_processes_valid_request_and_stops_after_empty_polls():
    source = Mock()
    source.get_next_request.side_effect = [
        '{"type": "create", "owner": "Jane Doe", "widgetId": "widget-123"}',
        None,
        None,
    ]
    storage = Mock()
    with patch("consumer.time.sleep"):
        poll(source, storage, max_empty_polls=2)

    storage.create.assert_called_once_with(REQUEST)
    assert source.get_next_request.call_count == 3

def test_poll_skips_invalid_request_and_continues_polling():
    source = Mock()
    source.get_next_request.side_effect = [
        "not valid json",
        None,
    ]
    storage = Mock()
    with patch("consumer.time.sleep"):
        poll(source, storage, max_empty_polls=1)

    storage.create.assert_not_called()
    assert source.get_next_request.call_count == 2

def test_poll_resets_empty_poll_count_after_request():
    source = Mock()
    source.get_next_request.side_effect = [
        None,
        '{"type": "create", "owner": "Jane Doe", "widgetId": "widget-123"}',
        None,
        None
    ]
    storage = Mock()
    with patch("consumer.time.sleep"):
        poll(source, storage, max_empty_polls=2)

    storage.create.assert_called_once_with(REQUEST)
    assert source.get_next_request.call_count == 4

def test_parse_args_accepts_s3_configuration():
    args = parse_args(
        [
            "--storage",
            "s3",
            "--request_bucket",
            "requests",
            "--widget_bucket",
            "widgets",
        ]
    )

    assert args.storage == "s3"
    assert args.request_bucket == "requests"
    assert args.widget_bucket == "widgets"
    assert args.max_empty_polls == 100

def test_parse_args_uses_default_dynamo_table():
    args = parse_args(
        [
            "--storage",
            "dynamo",
            "--request_bucket",
            "requests",
        ]
    )

    assert args.storage == "dynamo"
    assert args.table == "widgets"

def test_parse_args_requires_widget_bucket_for_s3():
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--storage",
                "s3",
                "--request_bucket",
                "requests",
            ]
        )