import json
from typing import Any, Dict


def safe_telegram_to_dict(obj: Any) -> Dict[str, Any]:
    """
    Safely convert Telegram object to dictionary, handling bytes and other non-serializable types
    """
    if hasattr(obj, 'to_dict'):
        raw_dict = obj.to_dict()
    else:
        raw_dict = obj.__dict__ if hasattr(obj, '__dict__') else str(obj)
    
    return _clean_dict(raw_dict)


def _clean_dict(data: Any) -> Any:
    """
    Recursively clean dictionary to make it JSON serializable
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if key.startswith('_'):
                continue  # Skip private attributes
            cleaned[key] = _clean_dict(value)
        return cleaned
    elif isinstance(data, list):
        return [_clean_dict(item) for item in data]
    elif isinstance(data, bytes):
        return f"<bytes:{len(data)}>"
    elif hasattr(data, 'isoformat'):  # datetime objects
        return data.isoformat()
    elif hasattr(data, '__dict__'):  # custom objects
        return _clean_dict(data.__dict__)
    else:
        try:
            json.dumps(data)  # Test if serializable
            return data
        except (TypeError, ValueError):
            return str(data) 