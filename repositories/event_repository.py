import base64
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.events.common import EventCommon

from models.event import Event
from utils import convert_telegram_obj


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_event(self, event: EventCommon):
        event_obj = Event(
            chat_id=getattr(event, "chat_id", 0),
            message_id=getattr(event, "_message_id", 0),
            event_json=convert_telegram_obj(event),
        )
        self.session.add(event_obj)
        return event_obj
