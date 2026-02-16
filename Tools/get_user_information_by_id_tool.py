import json

NAME = "get_user_information_by_id"

OPENAI_TOOL = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": (
            "Get user profile details by Telegram user id. "
            "Always check user info before responding."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user id",
                }
            },
            "required": ["user_id"],
        },
    },
}


async def execute(_context, arguments: dict) -> str:
    user_id = arguments.get("user_id")
    if user_id is None:
        return "Missing required argument: user_id"

    try:
        from telethon.tl.functions.users import GetFullUserRequest

        from dependency import dependency

        telethon_user = await dependency.telegram_client.get_entity(int(user_id))
        full = await dependency.telegram_client(GetFullUserRequest(id=telethon_user))
    except Exception as exc:
        return f"Failed to fetch full user {user_id} via Telethon: {exc}"

    if hasattr(full, "to_dict"):
        raw_full = full.to_dict()
    elif hasattr(full, "__dict__"):
        raw_full = full.__dict__
    else:
        raw_full = {"value": str(full)}
    return json.dumps(raw_full, ensure_ascii=False, default=str)
