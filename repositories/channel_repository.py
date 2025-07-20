from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.channel import Channel

class ChannelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_channel(self, channel_id: int, title: str, username: str | None = None, description: str | None = None, type_: str | None = None):
        result = await self.session.execute(select(Channel).where(Channel.id == channel_id))
        channel = result.scalar_one_or_none()
        if channel:
            channel.title = title
            channel.username = username
            channel.description = description
            channel.type = type_
        else:
            channel = Channel(id=channel_id, title=title, username=username, description=description, type=type_)
            self.session.add(channel)
        await self.session.commit()
        return channel

    async def get_channel(self, channel_id: int):
        result = await self.session.execute(select(Channel).where(Channel.id == channel_id))
        return result.scalar_one_or_none() 