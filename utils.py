import base64
from datetime import datetime


def convert_telegram_obj(obj):
    """Converts Telegram object to JSON-compatible format"""
    if isinstance(obj, dict):
        return {k: convert_telegram_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_telegram_obj(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode()
    elif hasattr(obj, "to_dict"):
        return convert_telegram_obj(obj.to_dict())
    else:
        return obj
