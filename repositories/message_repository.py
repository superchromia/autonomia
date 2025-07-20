from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.message import Message
from sqlalchemy import func, asc
from models.user import User

class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_message(self, message: Message):
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_message(self, channel_id: int, message_id: int):
        result = await self.session.execute(
            select(Message).where(
                Message.channel_id == channel_id,
                Message.message_id == message_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_messages(self, channel_id: int = None):
        stmt = select(Message)
        if channel_id:
            stmt = stmt.where(Message.channel_id == channel_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_messages_from_date(self, from_date, channel_id: int = None):
        stmt = select(Message, User.username).join(User, Message.sender_id == User.id, isouter=True).where(Message.date >= from_date)
        if channel_id is not None:
            stmt = stmt.where(Message.channel_id == channel_id)
        stmt = stmt.order_by(asc(Message.date))
        result = await self.session.execute(stmt)
        return [
            {
                "id": m.id,
                "channel_id": m.channel_id,
                "message_id": m.message_id,
                "sender_id": m.sender_id,
                "text": m.text,
                "date": m.date,
                "image_path": m.image_path,
                "username": username
            }
            for m, username in result.all()
        ]

    async def get_last_message_id(self, channel_id: int) -> int:
        result = await self.session.execute(
            select(func.max(Message.message_id)).where(Message.channel_id == channel_id)
        )
        return result.scalar() or 0 