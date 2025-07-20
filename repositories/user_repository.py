from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.user import User
from models.user_context import UserContext

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None, phone: str = None):
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.phone = phone
        else:
            user = User(id=user_id, username=username, first_name=first_name, last_name=last_name, phone=phone)
            self.session.add(user)
        await self.session.commit()
        return user

    async def get_user(self, user_id: int):
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def upsert_user_context(self, user_id: int, username: str = None, alias: str = None, role: str = None):
        result = await self.session.execute(select(UserContext).where(UserContext.id == user_id))
        ctx = result.scalar_one_or_none()
        if ctx:
            ctx.username = username
            ctx.alias = alias
            ctx.role = role
        else:
            ctx = UserContext(id=user_id, username=username, alias=alias, role=role)
            self.session.add(ctx)
        await self.session.commit()
        return ctx

    async def get_user_context(self, user_id: int):
        result = await self.session.execute(select(UserContext).where(UserContext.id == user_id))
        return result.scalar_one_or_none() 