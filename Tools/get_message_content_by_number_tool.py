import json

from models.message import Message

NAME = "get_message_content_by_number"

OPENAI_TOOL = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": (
            "Get message content by its message number (message_id) in current chat."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message_number": {
                    "type": "integer",
                    "description": "Message id/number in current chat",
                }
            },
            "required": ["message_number"],
        },
    },
}


async def execute(context, arguments: dict) -> str:
    from sqlalchemy.future import select

    message_number = arguments.get("message_number")
    if message_number is None:
        return "Missing required argument: message_number"

    result = await context.session.execute(
        select(Message).where(
            Message.chat_id == context.chat_id,
            Message.message_id == int(message_number),
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        return f"Message {message_number} not found in chat {context.chat_id}"

    text = None
    if isinstance(msg.raw_data, dict):
        text = msg.raw_data.get("message")
    return json.dumps(
        {
            "message_id": msg.message_id,
            "chat_id": msg.chat_id,
            "sender_id": msg.sender_id,
            "date": msg.date.isoformat() if msg.date else None,
            "text": text,
            "message_type": msg.message_type,
        },
        ensure_ascii=False,
    )
