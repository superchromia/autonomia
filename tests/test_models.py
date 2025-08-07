import pytest
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.future import select

from models.chat import Chat
from models.chat_config import ChatConfig
from models.message import Message
from models.messages_enriched import EnrichedMessage
from models.user import User


# Create test-specific models that use Text instead of JSONB
class TestChat(Chat):
    """Test version of Chat model using Text instead of JSONB."""

    __tablename__ = "chats"

    # Override raw_data to use Text instead of JSONB
    raw_data = Chat.__table__.c.raw_data.copy()
    raw_data.type = Text()


class TestMessage(Message):
    """Test version of Message model using Text instead of JSONB."""

    __tablename__ = "messages"

    # Override raw_data to use Text instead of JSONB
    raw_data = Message.__table__.c.raw_data.copy()
    raw_data.type = Text()


class TestUser(User):
    """Test version of User model using Text instead of JSONB."""

    __tablename__ = "users"

    # Override raw_data to use Text instead of JSONB
    raw_data = User.__table__.c.raw_data.copy()
    raw_data.type = Text()


class TestChatModel:
    """Test Chat model functionality."""

    @pytest.mark.asyncio
    async def test_create_chat(self, test_session, sample_chat_data):
        """Test creating a new chat."""
        # Convert raw_data to JSON string for Text field
        sample_chat_data["raw_data"] = '{"id": 123456789, "title": "Test Channel"}'

        chat = TestChat(**sample_chat_data)
        test_session.add(chat)
        await test_session.commit()

        result = await test_session.execute(select(TestChat).where(TestChat.id == sample_chat_data["id"]))
        saved_chat = result.scalar_one()

        assert saved_chat.id == sample_chat_data["id"]
        assert saved_chat.title == sample_chat_data["title"]
        assert saved_chat.username == sample_chat_data["username"]
        assert saved_chat.chat_type == sample_chat_data["chat_type"]

    @pytest.mark.asyncio
    async def test_chat_repr(self, test_session, sample_chat_data):
        """Test chat string representation."""
        # Convert raw_data to JSON string for Text field
        sample_chat_data["raw_data"] = '{"id": 123456789, "title": "Test Channel"}'

        chat = TestChat(**sample_chat_data)
        test_session.add(chat)
        await test_session.commit()

        repr_str = repr(chat)
        assert "Chat" in repr_str
        assert str(sample_chat_data["id"]) in repr_str
        assert sample_chat_data["title"] in repr_str


class TestUserModel:
    """Test User model functionality."""

    @pytest.mark.asyncio
    async def test_create_user(self, test_session, sample_user_data):
        """Test creating a new user."""
        # Convert raw_data to JSON string for Text field
        sample_user_data["raw_data"] = '{"id": 987654321, "first_name": "Test", "last_name": "User"}'

        user = TestUser(**sample_user_data)
        test_session.add(user)
        await test_session.commit()

        result = await test_session.execute(select(TestUser).where(TestUser.id == sample_user_data["id"]))
        saved_user = result.scalar_one()

        assert saved_user.id == sample_user_data["id"]
        assert saved_user.first_name == sample_user_data["first_name"]
        assert saved_user.username == sample_user_data["username"]

    @pytest.mark.asyncio
    async def test_user_full_name(self, test_session, sample_user_data):
        """Test user full name property."""
        # Convert raw_data to JSON string for Text field
        sample_user_data["raw_data"] = '{"id": 987654321, "first_name": "Test", "last_name": "User"}'

        user = TestUser(**sample_user_data)
        test_session.add(user)
        await test_session.commit()

        assert user.full_name == "Test User"

    @pytest.mark.asyncio
    async def test_user_chat_representation(self, test_session, sample_user_data):
        """Test user chat representation property."""
        # Convert raw_data to JSON string for Text field
        sample_user_data["raw_data"] = '{"id": 987654321, "first_name": "Test", "last_name": "User"}'

        user = TestUser(**sample_user_data)
        test_session.add(user)
        await test_session.commit()

        assert user.chat_representation == "@testuser"


class TestMessageModel:
    """Test Message model functionality."""

    @pytest.mark.asyncio
    async def test_create_message(self, test_session, sample_message_data):
        """Test creating a new message."""
        # Convert raw_data to JSON string for Text field
        sample_message_data["raw_data"] = '{"id": 111, "message": "Test message"}'

        message = TestMessage(**sample_message_data)
        test_session.add(message)
        await test_session.commit()

        result = await test_session.execute(
            select(TestMessage).where(TestMessage.message_id == sample_message_data["message_id"], TestMessage.chat_id == sample_message_data["chat_id"])
        )
        saved_message = result.scalar_one()

        assert saved_message.message_id == sample_message_data["message_id"]
        assert saved_message.chat_id == sample_message_data["chat_id"]
        assert saved_message.sender_id == sample_message_data["sender_id"]

    @pytest.mark.asyncio
    async def test_message_repr(self, test_session, sample_message_data):
        """Test message string representation."""
        # Convert raw_data to JSON string for Text field
        sample_message_data["raw_data"] = '{"id": 111, "message": "Test message"}'

        message = TestMessage(**sample_message_data)
        test_session.add(message)
        await test_session.commit()

        repr_str = repr(message)
        assert "Message" in repr_str
        assert str(sample_message_data["message_id"]) in repr_str


class TestEnrichedMessageModel:
    """Test EnrichedMessage model functionality."""

    @pytest.mark.asyncio
    async def test_create_enriched_message(self, test_session, sample_chat_data):
        """Test creating a new enriched message."""
        # First create a chat
        sample_chat_data["raw_data"] = '{"id": 123456789, "title": "Test Channel"}'
        chat = TestChat(**sample_chat_data)
        test_session.add(chat)
        await test_session.commit()

        # Create enriched message
        enriched_message_data = {
            "chat_id": sample_chat_data["id"],
            "message_id": 123,
            "context": "Test context",
            "meaning": "Test meaning",
            "embeddings": [0.1] * 4096,
        }

        enriched_message = EnrichedMessage(**enriched_message_data)
        test_session.add(enriched_message)
        await test_session.commit()

        result = await test_session.execute(
            select(EnrichedMessage).where(
                EnrichedMessage.chat_id == enriched_message_data["chat_id"], EnrichedMessage.message_id == enriched_message_data["message_id"]
            )
        )
        saved_enriched_message = result.scalar_one()

        assert saved_enriched_message.chat_id == enriched_message_data["chat_id"]
        assert saved_enriched_message.message_id == enriched_message_data["message_id"]
        assert saved_enriched_message.context == enriched_message_data["context"]
        assert saved_enriched_message.meaning == enriched_message_data["meaning"]


class TestChatConfigModel:
    """Test ChatConfig model functionality."""

    @pytest.mark.asyncio
    async def test_create_chat_config(self, test_session, sample_chat_data):
        """Test creating a new chat config."""
        # First create a chat
        sample_chat_data["raw_data"] = '{"id": 123456789, "title": "Test Channel"}'
        chat = TestChat(**sample_chat_data)
        test_session.add(chat)
        await test_session.commit()

        # Create chat config
        chat_config_data = {
            "chat_id": sample_chat_data["id"],
            "save_messages": True,
            "enrich_messages": True,
            "recognize_photo": False,
            "system_prompt": "Test prompt",
            "answer_threshold": 0.8,
        }

        chat_config = ChatConfig(**chat_config_data)
        test_session.add(chat_config)
        await test_session.commit()

        result = await test_session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat_config_data["chat_id"]))
        saved_chat_config = result.scalar_one()

        assert saved_chat_config.chat_id == chat_config_data["chat_id"]
        assert saved_chat_config.save_messages == chat_config_data["save_messages"]
        assert saved_chat_config.enrich_messages == chat_config_data["enrich_messages"]
        assert saved_chat_config.system_prompt == chat_config_data["system_prompt"]
