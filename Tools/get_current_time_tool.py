from datetime import UTC, datetime

NAME = "get_current_time"

OPENAI_TOOL = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Get current UTC time in ISO format.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


async def execute(_context, _arguments: dict) -> str:
    return datetime.now(UTC).isoformat()
