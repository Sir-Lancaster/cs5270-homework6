import json
import pytest
from parsing import parse_request


@pytest.mark.parametrize("request_type", ["create", "update", "delete"])
def test_parse_request_accepts_supported_request_types(request_type):
    request = {
        "type": request_type,
        "owner": "Jane Doe",
        "widgetId": "widget-123",
    }

    result = parse_request(json.dumps(request))
    assert result == request


def test_parse_request_preserves_optional_fields():
    request = {
        "type": "create",
        "owner": "Jane Doe",
        "widgetId": "widget-123",
        "requestId": "request-456",
        "label": "Temperature",
        "description": "Displays temperature",
        "otherAttributes": [
            {"name": "units", "value": "celsius"},
        ],
    }

    result = parse_request(json.dumps(request))
    assert result == request


def test_parse_request_returns_none_for_invalid_json():
    assert parse_request('{"type": "create"') is None


@pytest.mark.parametrize(
    "text",
    [
        "null",
        "[]",
        '"a string"',
        "123",
        "true",
    ],
)
def test_parse_request_returns_none_when_json_is_not_an_object(text):
    assert parse_request(text) is None

def test_parse_request_returns_none_for_unsupported_type():
    request = {
        "type": "read",
        "owner": "Jane Doe",
        "widgetId": "widget-123",
    }

    assert parse_request(json.dumps(request)) is None

@pytest.mark.parametrize(
    "missing_field",
    ["owner", "widgetId"],
)
def test_parse_request_returns_none_when_required_field_is_missing(missing_field):
    request = {
        "type": "create",
        "owner": "Jane Doe",
        "widgetId": "widget-123",
    }
    
    del request[missing_field]
    assert parse_request(json.dumps(request)) is None