import json
import logging

def parse_request(text):
    try:
        request = json.loads(text)
    except json.JSONDecodeError as e:
        logging.warning("Skipping request: invalid JSON (%s)", e)
        return None

    if not isinstance(request, dict):
        logging.warning("Skipping request: not a JSON object")
        return None

    if not request.get('type') in ("create", "update", "delete"):
        logging.warning("Skipping request: incorrect type")
        return None

    if "owner" not in request or "widgetId" not in request:
        logging.warning("Skipping request: missing owner or widget id")
        return None
    return request