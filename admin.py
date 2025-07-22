from sqladmin import Admin, ModelView

from models.chat import Chat
from models.chat_config import ChatConfig
from models.user import User


class ChatAdmin(ModelView, model=Chat):
    """Admin panel for Chat model"""

    name = "Chat"
    name_plural = "Chats"
    icon = "fa-solid fa-comments"

    column_list = [
        Chat.id,
        Chat.chat_type,
        Chat.title,
        Chat.username,
        Chat.is_verified,
        Chat.is_scam,
        Chat.is_fake,
        Chat.member_count,
        Chat.created_at,
        Chat.updated_at,
    ]

    column_searchable_list = [
        Chat.title,
        Chat.username,
    ]

    column_sortable_list = [
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

    form_excluded_columns = ["raw_data", "created_at", "updated_at"]


class UserAdmin(ModelView, model=User):
    """Admin panel for User model"""

    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    column_list = [
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

    column_searchable_list = [
        User.first_name,
        User.last_name,
        User.username,
    ]

    column_sortable_list = [
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

    form_excluded_columns = ["raw_data", "created_at", "updated_at"]


class ChatConfigAdmin(ModelView, model=ChatConfig):
    """Admin panel for ChatConfig model"""

    name = "Chat Configuration"
    name_plural = "Chat Configurations"
    icon = "fa-solid fa-cog"

    column_list = [
        ChatConfig.chat_id,
        ChatConfig.save_messages,
        ChatConfig.load_from_date,
        ChatConfig.system_prompt,
        ChatConfig.answer_threshold,
    ]

    column_searchable_list = [
        ChatConfig.chat_id,
    ]

    column_sortable_list = [
        ChatConfig.chat_id,
        ChatConfig.save_messages,
        ChatConfig.load_from_date,
    ]

    column_default_sort = ("chat_id", True)

    can_create = True
    can_edit = True
    can_delete = True


def setup_admin(app, engine):
    """Setup admin panel"""
    admin = Admin(app, engine, title="Superchromia Admin")

    # Add views
    admin.add_view(ChatAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(ChatConfigAdmin)

    return admin
