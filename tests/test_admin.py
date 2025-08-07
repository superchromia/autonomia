from unittest.mock import Mock, patch

import pytest

from admin import (
    AdminAuth,
    ChatAdmin,
    ChatConfigAdmin,
    EnrichedMessageAdmin,
    MediaAdmin,
    MessageAdmin,
    UserAdmin,
    setup_admin,
)
from models.chat import Chat
from models.chat_config import ChatConfig
from models.media import Media
from models.message import Message
from models.messages_enriched import EnrichedMessage
from models.user import User


class TestChatAdmin:
    """Test ChatAdmin functionality."""

    def test_chat_admin_creation(self):
        """Test that ChatAdmin can be instantiated."""
        admin = ChatAdmin()
        assert admin.name == "Chat"
        assert admin.name_plural == "Chats"
        assert admin.icon == "fa-solid fa-comments"

    def test_chat_admin_columns(self):
        """Test ChatAdmin column configuration."""
        admin = ChatAdmin()
        assert Chat.id in admin.column_list
        assert Chat.title in admin.column_list
        assert Chat.username in admin.column_list

    def test_chat_admin_permissions(self):
        """Test ChatAdmin permissions."""
        admin = ChatAdmin()
        assert admin.can_create is False
        assert admin.can_edit is True
        assert admin.can_delete is False


class TestUserAdmin:
    """Test UserAdmin functionality."""

    def test_user_admin_creation(self):
        """Test that UserAdmin can be instantiated."""
        admin = UserAdmin()
        assert admin.name == "User"
        assert admin.name_plural == "Users"
        assert admin.icon == "fa-solid fa-user"

    def test_user_admin_columns(self):
        """Test UserAdmin column configuration."""
        admin = UserAdmin()
        assert User.id in admin.column_list
        assert User.first_name in admin.column_list
        assert User.username in admin.column_list

    def test_user_admin_permissions(self):
        """Test UserAdmin permissions."""
        admin = UserAdmin()
        assert admin.can_create is False
        assert admin.can_edit is True
        assert admin.can_delete is False


class TestChatConfigAdmin:
    """Test ChatConfigAdmin functionality."""

    def test_chat_config_admin_creation(self):
        """Test that ChatConfigAdmin can be instantiated."""
        admin = ChatConfigAdmin()
        assert admin.name == "Chat Configuration"
        assert admin.name_plural == "Chat Configurations"
        assert admin.icon == "fa-solid fa-cog"

    def test_chat_config_admin_columns(self):
        """Test ChatConfigAdmin column configuration."""
        admin = ChatConfigAdmin()
        assert ChatConfig.chat_id in admin.column_list
        assert ChatConfig.enrich_messages in admin.column_list
        assert ChatConfig.recognize_photo in admin.column_list

    def test_chat_config_admin_permissions(self):
        """Test ChatConfigAdmin permissions."""
        admin = ChatConfigAdmin()
        assert admin.can_create is True
        assert admin.can_edit is True
        assert admin.can_delete is True

    def test_chat_config_admin_delete_model_exists(self):
        """Test ChatConfigAdmin delete_model method exists."""
        admin = ChatConfigAdmin()
        assert hasattr(admin, "delete_model")

    def test_chat_config_admin_get_url_for_exists(self):
        """Test ChatConfigAdmin get_url_for method exists."""
        admin = ChatConfigAdmin()
        assert hasattr(admin, "get_url_for")


class TestMediaAdmin:
    """Test MediaAdmin functionality."""

    def test_media_admin_creation(self):
        """Test that MediaAdmin can be instantiated."""
        admin = MediaAdmin()
        assert admin.name == "Media"
        assert admin.name_plural == "Media"
        assert admin.icon == "fa-solid fa-image"

    def test_media_admin_columns(self):
        """Test MediaAdmin column configuration."""
        admin = MediaAdmin()
        assert Media.file_reference in admin.column_list
        assert Media.chat_id in admin.column_list
        assert Media.media_type in admin.column_list

    def test_media_admin_permissions(self):
        """Test MediaAdmin permissions."""
        admin = MediaAdmin()
        assert admin.can_create is True
        assert admin.can_edit is True
        assert admin.can_delete is True


class TestMessageAdmin:
    """Test MessageAdmin functionality."""

    def test_message_admin_creation(self):
        """Test that MessageAdmin can be instantiated."""
        admin = MessageAdmin()
        assert admin.name == "Message"
        assert admin.name_plural == "Messages"
        assert admin.icon == "fa-solid fa-comment"

    def test_message_admin_columns(self):
        """Test MessageAdmin column configuration."""
        admin = MessageAdmin()
        assert Message.message_id in admin.column_list
        assert Message.chat_id in admin.column_list
        assert Message.message_type in admin.column_list

    def test_message_admin_permissions(self):
        """Test MessageAdmin permissions."""
        admin = MessageAdmin()
        assert admin.can_create is False
        assert admin.can_edit is True
        assert admin.can_delete is False


class TestEnrichedMessageAdmin:
    """Test EnrichedMessageAdmin functionality."""

    def test_enriched_message_admin_creation(self):
        """Test that EnrichedMessageAdmin can be instantiated."""
        admin = EnrichedMessageAdmin()
        assert admin.name == "Enriched Message"
        assert admin.name_plural == "Enriched Messages"
        assert admin.icon == "fa-solid fa-brain"

    def test_enriched_message_admin_columns(self):
        """Test EnrichedMessageAdmin column configuration."""
        admin = EnrichedMessageAdmin()
        assert EnrichedMessage.chat_id in admin.column_list
        assert EnrichedMessage.message_id in admin.column_list
        assert "has_embeddings" in admin.column_list

    def test_enriched_message_admin_permissions(self):
        """Test EnrichedMessageAdmin permissions."""
        admin = EnrichedMessageAdmin()
        assert admin.can_create is False
        assert admin.can_edit is True
        assert admin.can_delete is False

    def test_has_embeddings_method(self):
        """Test has_embeddings method."""
        admin = EnrichedMessageAdmin()

        # Test with embeddings
        mock_obj = Mock()
        mock_obj.embeddings = [0.1, 0.2, 0.3]
        result = admin.has_embeddings(mock_obj)
        assert result == "Yes"

        # Test without embeddings
        mock_obj.embeddings = None
        result = admin.has_embeddings(mock_obj)
        assert result == "No"


class TestAdminAuth:
    """Test AdminAuth functionality."""

    def test_admin_auth_methods_exist(self):
        """Test that AdminAuth methods exist."""
        auth = AdminAuth(secret_key="test-secret")
        assert hasattr(auth, "login")
        assert hasattr(auth, "logout")
        assert hasattr(auth, "authenticate")

    @pytest.mark.asyncio
    async def test_admin_auth_logout(self):
        """Test admin logout."""
        auth = AdminAuth(secret_key="test-secret")

        mock_request = Mock()
        mock_request.session = {"admin_auth": True}

        result = await auth.logout(mock_request)
        assert result is True
        assert mock_request.session == {}

    @pytest.mark.asyncio
    async def test_admin_auth_authenticate(self):
        """Test admin authentication check."""
        auth = AdminAuth(secret_key="test-secret")

        # Test authenticated
        mock_request = Mock()
        mock_request.session = {"admin_auth": True}
        result = await auth.authenticate(mock_request)
        assert result is True

        # Test not authenticated
        mock_request.session = {}
        result = await auth.authenticate(mock_request)
        assert result is False


class TestSetupAdmin:
    """Test setup_admin function."""

    def test_setup_admin(self):
        """Test setup_admin function."""
        mock_app = Mock()
        mock_engine = Mock()

        # Mock config
        with patch("admin.config") as mock_config:
            mock_config.secret_key = "test-secret"
            mock_config.force_https = True

            result = setup_admin(mock_app, mock_engine)

            # Verify admin was created
            assert result is not None
            assert hasattr(result, "add_view")


def test_admin_imports():
    """Test that all admin classes can be imported."""
    assert ChatAdmin is not None
    assert UserAdmin is not None
    assert ChatConfigAdmin is not None
    assert MediaAdmin is not None
    assert MessageAdmin is not None
    assert EnrichedMessageAdmin is not None
    assert AdminAuth is not None
    assert setup_admin is not None
