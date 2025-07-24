import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.tl.types import User

from models.user import User as UserModel
from utils import convert_telegram_obj

logger = logging.getLogger("user_repository")


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_user(self, user: User) -> UserModel:
        async with self.session.begin():
            user_data = convert_telegram_obj(user)
            user_obj = UserModel(
                id=user.id,
                username=getattr(user, "username", None),
                first_name=getattr(user, "first_name", None),
                last_name=getattr(user, "last_name", None),
                is_verified=getattr(user, "verified", False),
                is_scam=getattr(user, "scam", False),
                is_fake=getattr(user, "fake", False),
                is_bot=getattr(user, "bot", False),
                is_premium=getattr(user, "premium", False),
                raw_data=user_data,
            )

            await self.session.merge(user_obj)
            return user_obj

    async def list_all(self) -> list[UserModel]:
        """Get all users"""
        result = await self.session.execute(
            select(UserModel).order_by(UserModel.id)
        )
        return result.scalars().all()

    async def get(self, user_id: int) -> UserModel | None:
        """Get user by ID"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()
