from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.events.common import EventCommon

from models.event import Event
from utils import convert_telegram_obj


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_event(self, event: EventCommon):
        async with self.session.begin():
            event_obj = dict(
                chat_id=getattr(event, "chat_id", 0),
                message_id=getattr(event, "_message_id", 0),
                event_json=convert_telegram_obj(event),
            )
            stmt = insert(Event).values(event_obj).on_conflict_do_nothing()
            await self.session.execute(stmt)
            return event_obj
