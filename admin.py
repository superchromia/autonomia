from typing import ClassVar

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from config import config
from models.chat import Chat
from models.chat_config import ChatConfig
from models.media import Media
from models.message import Message
from models.messages_enriched import EnrichedMessage
from models.user import User


class ChatAdmin(ModelView, model=Chat):
    """Admin panel for Chat model"""

    name = "Chat"
    name_plural = "Chats"
    icon = "fa-solid fa-comments"

    column_list: ClassVar = [
        Chat.id,
        Chat.chat_type,
        Chat.title,
        Chat.username,
        Chat.is_verified,
        Chat.is_scam,
        Chat.is_fake,
        Chat.member_count,
        Chat.messages_count,
        Chat.enriched_messages_count,
        Chat.created_at,
        Chat.updated_at,
    ]

    column_searchable_list: ClassVar = [
        Chat.title,
        Chat.username,
    ]

    column_sortable_list: ClassVar = [
        Chat.id,
        Chat.chat_type,
        Chat.title,
        Chat.created_at,
        Chat.updated_at,
    ]

    column_default_sort = ("created_at", True)

    can_create = False
    can_edit = True
    can_delete = False

    form_excluded_columns: ClassVar = ["raw_data", "created_at", "updated_at"]


class UserAdmin(ModelView, model=User):
    """Admin panel for User model"""

    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    column_list: ClassVar = [
        User.id,
        User.first_name,
        User.last_name,
        User.username,
        User.is_bot,
        User.is_verified,
        User.is_scam,
        User.is_fake,
        User.is_premium,
        User.created_at,
        User.updated_at,
    ]

    column_searchable_list: ClassVar = [
        User.first_name,
        User.last_name,
        User.username,
    ]

    column_sortable_list: ClassVar = [
        User.id,
        User.first_name,
        User.username,
        User.is_bot,
        User.created_at,
        User.updated_at,
    ]

    column_default_sort = ("created_at", True)

    can_create = False
    can_edit = True
    can_delete = False

    form_excluded_columns: ClassVar = ["raw_data", "created_at", "updated_at"]


class ChatConfigAdmin(ModelView, model=ChatConfig):
    """Admin panel for ChatConfig model"""

    name = "Chat Configuration"
    name_plural = "Chat Configurations"
    icon = "fa-solid fa-cog"

    column_list: ClassVar = [
        ChatConfig.chat_id,
        ChatConfig.enrich_messages,
        ChatConfig.recognize_photo,
    ]

    column_searchable_list: ClassVar = [
        ChatConfig.chat_id,
    ]

    column_sortable_list: ClassVar = [
        ChatConfig.chat_id,
        ChatConfig.enrich_messages,
        ChatConfig.recognize_photo,
    ]

    form_include_pk = True

    column_default_sort = ("chat_id", True)

    can_create = True
    can_edit = True
    can_delete = True

    def get_url_for(self, name: str, **kwargs) -> str:
        """Override to ensure HTTPS URLs are used."""
        url = super().get_url_for(name, **kwargs)
        if config.force_https and url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
        return url


class MediaAdmin(ModelView, model=Media):
    """Admin panel for Media model"""

    name = "Media"
    name_plural = "Media"
    icon = "fa-solid fa-image"

    column_list: ClassVar = [
        Media.file_reference,
        Media.chat_id,
        Media.message_id,
        Media.media_type,
        Media.text_description,
        Media.created_at,
        Media.updated_at,
    ]

    column_searchable_list: ClassVar = [
        Media.file_reference,
        Media.chat_id,
        Media.message_id,
        Media.media_type,
        Media.text_description,
    ]

    column_sortable_list: ClassVar = [
        Media.file_reference,
        Media.chat_id,
        Media.message_id,
        Media.media_type,
        Media.created_at,
        Media.updated_at,
    ]

    column_default_sort = ("created_at", True)

    can_create = True
    can_edit = True
    can_delete = True

    form_excluded_columns: ClassVar = ["created_at", "updated_at"]


class MessageAdmin(ModelView, model=Message):
    """Admin panel for Message model"""

    name = "Message"
    name_plural = "Messages"
    icon = "fa-solid fa-comment"

    column_list: ClassVar = [
        Message.message_id,
        Message.chat_id,
        Message.sender_id,
        Message.date,
        Message.message_type,
        Message.is_read,
        Message.is_deleted,
        Message.created_at,
        Message.updated_at,
    ]

    column_searchable_list: ClassVar = [
        Message.message_id,
        Message.chat_id,
        Message.sender_id,
        Message.message_type,
    ]

    column_sortable_list: ClassVar = [
        Message.message_id,
        Message.chat_id,
        Message.sender_id,
        Message.date,
        Message.message_type,
        Message.is_read,
        Message.created_at,
        Message.updated_at,
    ]

    column_default_sort = ("date", True)

    can_create = False
    can_edit = True
    can_delete = False

    form_excluded_columns: ClassVar = ["raw_data", "created_at", "updated_at"]


class EnrichedMessageAdmin(ModelView, model=EnrichedMessage):
    """Admin panel for EnrichedMessage model"""

    name = "Enriched Message"
    name_plural = "Enriched Messages"
    icon = "fa-solid fa-brain"

    column_list: ClassVar = [
        EnrichedMessage.chat_id,
        EnrichedMessage.message_id,
        EnrichedMessage.context,
        EnrichedMessage.meaning,
        "has_embeddings",
    ]

    column_searchable_list: ClassVar = [
        EnrichedMessage.chat_id,
        EnrichedMessage.message_id,
        EnrichedMessage.context,
        EnrichedMessage.meaning,
    ]

    column_sortable_list: ClassVar = [
        EnrichedMessage.chat_id,
        EnrichedMessage.message_id,
    ]

    column_default_sort = ("chat_id", True)

    can_create = False
    can_edit = True
    can_delete = False

    form_excluded_columns: ClassVar = ["embeddings"]
    column_details_exclude_list: ClassVar = ["embeddings"]

    def has_embeddings(self, obj: EnrichedMessage) -> str:
        """Check if message has embeddings"""
        return "Yes" if obj.embeddings is not None else "No"


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]

        if username == config.admin_username and password == config.admin_password:
            request.session.update({"admin_auth": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin_auth", False)


def setup_admin(app, engine):
    """Setup admin panel with authentication"""
    # Create authentication backend
    auth_backend = AdminAuth(secret_key=config.secret_key)

    # Create admin with authentication and HTTPS support
    admin = Admin(
        app,
        engine,
        title="Superchromia Admin",
        authentication_backend=auth_backend,
        base_url="/admin" if config.force_https else None,
    )

    # Add views
    admin.add_view(ChatAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(ChatConfigAdmin)
    admin.add_view(MediaAdmin)
    admin.add_view(MessageAdmin)
    admin.add_view(EnrichedMessageAdmin)

    return admin
