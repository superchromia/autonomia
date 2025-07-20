import base64
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.events import NewMessage
from typing import Any
from models.event import Event


def convert_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: convert_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_obj(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode('ascii')
    elif hasattr(obj, 'to_dict'):
        return convert_obj(obj.to_dict())
    else:
        return obj

class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_event(self, event: NewMessage.Event):
        event_obj = Event(
            chat_id=event.chat_id,
            sender_id=event.sender_id,
            message_id=event._message_id,
            utc_dttm=event.date.replace(tzinfo=None),
            event_json=convert_obj(event.to_dict())
        )
        self.session.add(event_obj)
        return event_obj 

    async def get_last_message_id(self, chat_id):
        result = await self.session.execute(
            select(func.max(Event.message_id)).where(Event.chat_id == chat_id)
        )
        return result.scalar() or 0
        