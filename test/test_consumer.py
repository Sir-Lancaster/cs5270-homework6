from unittest.mock import Mock, patch
import pytest
from consumer import parse_args, poll, processRequest



def test_process_request_dispatches_create_to_storage():
    storage = Mock()
    REQUEST = {
        "type": "create",
        "owner": "Jane Doe",
        "widgetId": "widget-123",
    }
    processRequest(REQUEST, storage)
    storage.create.assert_called_once_with(REQUEST)
    storage.update.assert_not_called()
    storage.delete.assert_not_called()

def test_process_request_dispatches_delete_to_storage():
    storage = Mock()
    REQUEST = {
        "type": "delete",
        "owner": "Jane Doe",
        "widgetId": "widget-123",
    }
    processRequest(REQUEST, storage)
    storage.delete.assert_called_once_with(REQUEST)
    storage.update.assert_not_called()
    storage.create.assert_not_called()

def test_process_request_dispatches_update_to_storage():
    storage = Mock()
    REQUEST = {
        "type": "update",
        "owner": "Jane Doe",
        "widgetId": "widget-123",
    }
    processRequest(REQUEST, storage)
    storage.update.assert_called_once_with(REQUEST)
    storage.create.assert_not_called()
    storage.delete.assert_not_called()

def test_poll_processes_valid_request_and_stops_after_empty_polls():
    source = Mock()
    REQUEST = {
        "type": "create",
        "owner": "Jane Doe",
        "widgetId": "widget-123",
    }
    source.get_next_request.side_effect = [
        ('{"type": "create", "owner": "Jane Doe", "widgetId": "widget-123"}', "h1"),
        None,
        None,
    ]
    storage = Mock()
    with patch("consumer.time.sleep"):
        poll(source, storage, max_empty_polls=2)

    storage.create.assert_called_once_with(REQUEST)
    source.complete.assert_called_once_with("h1")
    assert source.get_next_request.call_count == 3

def test_poll_skips_invalid_request_and_continues_polling():
    source = Mock()
    source.get_next_request.side_effect = [
        ("not valid json", "h1"),
        None,
    ]
    storage = Mock()
    with patch("consumer.time.sleep"):
        poll(source, storage, max_empty_polls=1)

    storage.create.assert_not_called()
    source.complete.assert_called_once_with("h1")
    assert source.get_next_request.call_count == 2

def test_poll_resets_empty_poll_count_after_request():
    source = Mock()
    REQUEST = {
        "type": "create",
        "owner": "Jane Doe",
        "widgetId": "widget-123",
    }
    source.get_next_request.side_effect = [
        None,
        ('{"type": "create", "owner": "Jane Doe", "widgetId": "widget-123"}', "h1"),
        None,
        None
    ]
    storage = Mock()
    with patch("consumer.time.sleep"):
        poll(source, storage, max_empty_polls=2)

    storage.create.assert_called_once_with(REQUEST)
    assert source.get_next_request.call_count == 4

def test_poll_does_not_complete_request_when_processing_fails():
    source = Mock()
    storage = Mock()
    source.get_next_request.side_effect = [
        ('{"type": "create", "owner": "Jane Doe", "widgetId": "widget-123"}', "h1"),
        None
    ]
    storage.create.side_effect = Exception("Boom")
    with patch("consumer.time.sleep"):
        poll(source, storage, max_empty_polls=2)

    source.complete.assert_not_called()

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

def test_parse_args_with_queue_option():
    args = parse_args(
        [
            "--queue",
            "requests",
            "--storage",
            "dynamo"
        ]
    )

    assert args.queue == "requests"
    assert args.request_bucket is None

def test_parse_args_with_queue_option_and_request_bucket_fails():
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--queue",
                "requests",
                "--storage",
                "dynamo",
                "--request_bucket",
                "requests"
            ]
        )