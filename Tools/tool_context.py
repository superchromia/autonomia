from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ToolExecutionContext:
    session: AsyncSession
    chat_id: int
    current_message_id: int | None = None
    current_sender_id: int | None = None
    current_chat_type: str | None = None
