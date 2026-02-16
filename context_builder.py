import logging

from models.chat import Chat
from models.memory import Memory
from models.message import Message

# pylint: disable=broad-exception-caught


logger = logging.getLogger("context_builder")


def format_message(raw_data, username):
    """
    Formats message from raw_data as:
    'Сообщение {id}: от {username}: "{text}"'
    or for replies:
    'Сообщение {id}: от {username} на id={reply_to}: "{text}"'
    """
    msg_id = raw_data.get("id")
    msg_text = raw_data.get("message", "")

    reply_to = None
    if "reply_to" in raw_data and isinstance(raw_data["reply_to"], dict):
        reply_to = raw_data["reply_to"].get("reply_to_msg_id")

    if reply_to:
        return f"Сообщение {msg_id}: " f'от {username} на id={reply_to}: "{msg_text}"'
    return f'Сообщение {msg_id}: от {username}: "{msg_text}"'


class ContextBuilder:
    def __init__(self, session, chat_id: int, message_id: int):
        self.session = session
        self.chat_id = chat_id
        self.message_id = message_id

    async def build(self) -> str:
        message = await self._get_current_message()
        if not message:
            return "Message not found"

        previous_messages = await self._get_previous_messages()
        previous_messages_formatted = "\n".join(format_message(msg.raw_data, msg.sender_id) for msg in previous_messages)
        current_message_text = format_message(
            message.raw_data,
            message.sender_id,
        )
        return self._render_context(
            previous_messages_formatted=previous_messages_formatted,
            current_message_text=current_message_text,
        )

    async def _get_current_message(self) -> Message | None:
        from sqlalchemy.future import select

        result = await self.session.execute(
            select(Message).where(
                Message.chat_id == self.chat_id,
                Message.message_id == self.message_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_previous_messages(self) -> list[Message]:
        from sqlalchemy.future import select

        result = await self.session.execute(
            select(Message)
            .where(
                Message.chat_id == self.chat_id,
                Message.message_id < self.message_id,
            )
            .order_by(Message.message_id.desc())
            .limit(50)
        )
        return result.scalars().all()

    async def _is_direct_user_chat(self) -> bool:
        from sqlalchemy.future import select

        result = await self.session.execute(select(Chat).where(Chat.id == self.chat_id))
        chat = result.scalar_one_or_none()
        return bool(chat and isinstance(chat.chat_type, str) and chat.chat_type.lower() == "user")

    async def _collect_chat_memories(self, limit: int = 20) -> str:
        from sqlalchemy.future import select

        try:
            result = await self.session.execute(
                select(Memory)
                .where(
                    Memory.chat_id == self.chat_id,
                    Memory.user_id.is_(None),
                    Memory.is_active.is_(True),
                )
                .order_by(Memory.importance.desc(), Memory.updated_at.desc())
                .limit(limit)
            )
            memories = result.scalars().all()
        except Exception as exc:
            logger.warning(
                "Failed to load chat memories for chat %s: %s",
                self.chat_id,
                exc,
            )
            return ""

        if not memories:
            return ""
        return "\n".join(self._format_memory_line(memory) for memory in memories)

    async def _collect_user_memories(
        self,
        user_id: int | None,
        limit: int = 20,
    ) -> str:
        from sqlalchemy.future import select

        if user_id is None:
            return ""

        try:
            result = await self.session.execute(
                select(Memory)
                .where(
                    Memory.user_id == user_id,
                    Memory.is_active.is_(True),
                )
                .order_by(Memory.importance.desc(), Memory.updated_at.desc())
                .limit(limit)
            )
            memories = result.scalars().all()
        except Exception as exc:
            logger.warning(
                "Failed to load user memories for user %s: %s",
                user_id,
                exc,
            )
            return ""

        if not memories:
            return ""
        return "\n".join(self._format_memory_line(memory) for memory in memories)

    @staticmethod
    def _format_memory_line(memory: Memory) -> str:
        source_position = memory.source_message_position or memory.source_message_id
        source_part = f" @msg={source_position}" if source_position is not None else ""
        return f"- [{memory.memory_type}|{memory.importance}/10]" f"{source_part} {memory.memory_text}"

    @staticmethod
    def _render_context(
        *,
        previous_messages_formatted: str,
        current_message_text: str,
    ) -> str:
        return f"""
    ПРЕДЫДУЩИЕ СООБЩЕНИЯ:
    {previous_messages_formatted}

    ТЕКУЩЕЕ СООБЩЕНИЕ:
    {current_message_text}
    """


async def collect_chat_memories(session, chat_id: int, limit: int = 20) -> str:
    builder = ContextBuilder(session, chat_id=chat_id, message_id=0)
    return await builder._collect_chat_memories(limit=limit)  # noqa: SLF001


async def collect_user_memories(
    session,
    user_id: int | None,
    limit: int = 20,
) -> str:
    if user_id is None:
        return ""
    builder = ContextBuilder(session, chat_id=0, message_id=0)
    return await builder._collect_user_memories(user_id, limit=limit)  # noqa: SLF001


async def collect_message_context(session, chat_id: int, message_id: int) -> str:
    builder = ContextBuilder(
        session=session,
        chat_id=chat_id,
        message_id=message_id,
    )
    return await builder.build()
