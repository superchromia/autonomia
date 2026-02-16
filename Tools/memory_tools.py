import json

from models.memory import Memory

SAVE_MEMORY_NAME = "save_memory"
GET_USER_MEMORIES_NAME = "get_user_memories"
GET_CHAT_MEMORIES_NAME = "get_chat_memories"

SAVE_MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": SAVE_MEMORY_NAME,
        "description": (
            "Save important long-term memory. "
            "Can save chat memory, user memory, or both."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "memory_text": {
                    "type": "string",
                    "description": "Fact/rule/preference to remember",
                },
                "memory_type": {
                    "type": "string",
                    "description": "fact, rule, or preference",
                },
                "importance": {
                    "type": "integer",
                    "description": "Importance from 1 to 10",
                },
                "source_message_id": {
                    "type": "integer",
                    "description": "Message id where memory came from",
                },
                "source_message_position": {
                    "type": "integer",
                    "description": "Position/order id of source message in chat",
                },
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user id for user-specific memory",
                },
                "memory_scope": {
                    "type": "string",
                    "description": "chat, user, or both",
                },
            },
            "required": ["memory_text"],
        },
    },
}

GET_USER_MEMORIES_TOOL = {
    "type": "function",
    "function": {
        "name": GET_USER_MEMORIES_NAME,
        "description": "Get all active long-term memories about a specific user.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user id",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return",
                },
            },
            "required": ["user_id"],
        },
    },
}

GET_CHAT_MEMORIES_TOOL = {
    "type": "function",
    "function": {
        "name": GET_CHAT_MEMORIES_NAME,
        "description": "Get active long-term memories for the current chat.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return",
                }
            },
        },
    },
}


def _normalize_memory_type(value: str | None) -> str:
    memory_type = (value or "fact").strip().lower()
    if memory_type not in {"fact", "rule", "preference"}:
        return "fact"
    return memory_type


def _normalize_int(value, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def save_memory(context, arguments: dict) -> str:
    from sqlalchemy.future import select

    memory_text = (arguments.get("memory_text") or "").strip()
    if not memory_text:
        return "Missing required argument: memory_text"

    memory_type = _normalize_memory_type(arguments.get("memory_type"))
    importance = _normalize_int(arguments.get("importance"), default=7) or 7
    importance = max(1, min(10, importance))

    source_message_id = _normalize_int(
        arguments.get("source_message_id"),
        default=context.current_message_id,
    )
    source_message_position = _normalize_int(
        arguments.get("source_message_position"),
        default=source_message_id,
    )
    target_user_id = _normalize_int(
        arguments.get("user_id"),
        default=context.current_sender_id,
    )

    memory_scope = (arguments.get("memory_scope") or "both").strip().lower()
    if memory_scope not in {"chat", "user", "both"}:
        memory_scope = "both"

    if context.current_chat_type and context.current_chat_type.lower() == "user" and memory_scope == "both":
        memory_scope = "user"

    scopes_to_save: list[str] = []
    if memory_scope in {"chat", "both"}:
        scopes_to_save.append("chat")
    if memory_scope in {"user", "both"} and target_user_id is not None:
        scopes_to_save.append("user")

    if not scopes_to_save:
        return "No valid memory scope to save"

    saved_items: list[dict] = []
    for scope in scopes_to_save:
        if scope == "chat":
            existing_result = await context.session.execute(
                select(Memory).where(
                    Memory.chat_id == context.chat_id,
                    Memory.user_id.is_(None),
                    Memory.memory_text == memory_text,
                    Memory.is_active.is_(True),
                )
            )
            existing_memory = existing_result.scalar_one_or_none()
            if existing_memory:
                existing_memory.memory_type = memory_type
                existing_memory.importance = max(existing_memory.importance, importance)
                if source_message_id is not None:
                    existing_memory.source_message_id = source_message_id
                if source_message_position is not None:
                    existing_memory.source_message_position = source_message_position
                saved_items.append(
                    {
                        "scope": "chat",
                        "status": "updated",
                        "memory_id": existing_memory.id,
                    }
                )
                continue

            memory = Memory(
                chat_id=context.chat_id,
                user_id=None,
                source_message_id=source_message_id,
                source_message_position=source_message_position,
                memory_text=memory_text,
                memory_type=memory_type,
                importance=importance,
                is_active=True,
            )
            context.session.add(memory)
            await context.session.flush()
            saved_items.append(
                {
                    "scope": "chat",
                    "status": "saved",
                    "memory_id": memory.id,
                }
            )
            continue

        existing_result = await context.session.execute(
            select(Memory).where(
                Memory.user_id == target_user_id,
                Memory.memory_text == memory_text,
                Memory.is_active.is_(True),
            )
        )
        existing_memory = existing_result.scalar_one_or_none()
        if existing_memory:
            existing_memory.memory_type = memory_type
            existing_memory.importance = max(existing_memory.importance, importance)
            if source_message_id is not None:
                existing_memory.source_message_id = source_message_id
            if source_message_position is not None:
                existing_memory.source_message_position = source_message_position
            saved_items.append(
                {
                    "scope": "user",
                    "status": "updated",
                    "memory_id": existing_memory.id,
                }
            )
            continue

        memory = Memory(
            chat_id=context.chat_id,
            user_id=target_user_id,
            source_message_id=source_message_id,
            source_message_position=source_message_position,
            memory_text=memory_text,
            memory_type=memory_type,
            importance=importance,
            is_active=True,
        )
        context.session.add(memory)
        await context.session.flush()
        saved_items.append(
            {
                "scope": "user",
                "status": "saved",
                "memory_id": memory.id,
                "user_id": target_user_id,
            }
        )

    await context.session.commit()
    return json.dumps(
        {
            "status": "ok",
            "memory_text": memory_text,
            "saved_items": saved_items,
            "source_message_id": source_message_id,
            "source_message_position": source_message_position,
        },
        ensure_ascii=False,
    )


async def get_user_memories(context, arguments: dict) -> str:
    from sqlalchemy.future import select

    user_id = arguments.get("user_id")
    if user_id is None:
        return "Missing required argument: user_id"
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return "Invalid user_id"

    limit = arguments.get("limit", 50)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(200, limit))

    result = await context.session.execute(
        select(Memory)
        .where(
            Memory.user_id == user_id,
            Memory.is_active.is_(True),
        )
        .order_by(Memory.importance.desc(), Memory.updated_at.desc())
        .limit(limit)
    )
    memories = result.scalars().all()
    return json.dumps(
        {
            "user_id": user_id,
            "memories": [
                {
                    "id": memory.id,
                    "chat_id": memory.chat_id,
                    "memory_text": memory.memory_text,
                    "memory_type": memory.memory_type,
                    "importance": memory.importance,
                    "source_message_id": memory.source_message_id,
                    "source_message_position": memory.source_message_position,
                }
                for memory in memories
            ],
        },
        ensure_ascii=False,
    )


async def get_chat_memories(context, arguments: dict) -> str:
    from sqlalchemy.future import select

    limit = arguments.get("limit", 50)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(200, limit))

    result = await context.session.execute(
        select(Memory)
        .where(
            Memory.chat_id == context.chat_id,
            Memory.user_id.is_(None),
            Memory.is_active.is_(True),
        )
        .order_by(Memory.importance.desc(), Memory.updated_at.desc())
        .limit(limit)
    )
    memories = result.scalars().all()
    return json.dumps(
        {
            "chat_id": context.chat_id,
            "memories": [
                {
                    "id": memory.id,
                    "memory_text": memory.memory_text,
                    "memory_type": memory.memory_type,
                    "importance": memory.importance,
                    "source_message_id": memory.source_message_id,
                    "source_message_position": memory.source_message_position,
                }
                for memory in memories
            ],
        },
        ensure_ascii=False,
    )
