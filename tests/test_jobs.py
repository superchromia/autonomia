import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telethon import types

from jobs.sync_dialogs import sync_dialogs_job
from jobs.telethon_hook import new_message_handler, message_edited_handler, message_deleted_handler
from models.chat import Chat
from models.user import User
from models.message import Message
from models.chat_config import ChatConfig


class TestSyncDialogsJob:
    """Test sync dialogs job functionality."""
    
    @pytest.mark.asyncio
    @patch('jobs.sync_dialogs.dependency')
    async def test_sync_dialogs_job_no_client(self, mock_dependency, test_session):
        """Test sync dialogs job when telegram client is not available."""
        mock_dependency.telegram_client = None
        
        # Should not raise any exception
        await sync_dialogs_job()
    
    @pytest.mark.asyncio
    @patch('jobs.sync_dialogs.dependency')
    async def test_sync_dialogs_job_with_client(self, mock_dependency, test_session, sample_chat_data, sample_user_data):
        """Test sync dialogs job with telegram client."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_dependency.telegram_client = mock_client
        mock_dependency.get_session.return_value.__aiter__.return_value = [test_session]
        
        # Create mock dialog
        mock_dialog = MagicMock()
        mock_dialog.name = "Test Dialog"
        mock_dialog.entity = MagicMock()
        mock_dialog.entity.id = sample_chat_data["id"]
        mock_dialog.entity.__class__.__name__ = "Channel"
        mock_dialog.entity.title = sample_chat_data["title"]
        mock_dialog.entity.username = sample_chat_data["username"]
        mock_dialog.entity.verified = sample_chat_data["is_verified"]
        mock_dialog.entity.scam = sample_chat_data["is_scam"]
        mock_dialog.entity.fake = sample_chat_data["is_fake"]
        mock_dialog.entity.participants_count = sample_chat_data["member_count"]
        
        # Create proper async iterator for dialogs
        async def mock_iter_dialogs():
            yield mock_dialog
        
        mock_client.iter_dialogs.return_value = mock_iter_dialogs()
        
        # Create proper async iterator for participants
        async def mock_iter_participants():
            return
        
        mock_client.iter_participants.return_value = mock_iter_participants()
        
        # Run job
        await sync_dialogs_job()
        
        # Verify chat was created
        from sqlalchemy.future import select
        result = await test_session.execute(select(Chat).where(Chat.id == sample_chat_data["id"]))
        saved_chat = result.scalar_one_or_none()
        
        assert saved_chat is not None
        assert saved_chat.title == sample_chat_data["title"]
        assert saved_chat.username == sample_chat_data["username"]


class TestTelethonHook:
    """Test telethon hook functionality."""
    
    @pytest.mark.asyncio
    @patch('jobs.telethon_hook.dependency')
    async def test_new_message_handler(self, mock_dependency, test_session, sample_chat_data, sample_user_data):
        """Test new message handler."""
        # Setup mock dependency
        mock_dependency.get_session.return_value.__aiter__.return_value = [test_session]
        mock_dependency.telegram_client = AsyncMock()
        
        # Create mock event
        mock_event = MagicMock()
        mock_message = MagicMock()
        mock_message.id = 123
        mock_message.date = "2024-01-01T12:00:00Z"
        mock_message.media = None
        mock_message.raw_data = {"id": 123, "message": "Test message"}
        mock_event.message = mock_message
        
        # Create mock chat
        mock_chat = MagicMock()
        mock_chat.id = sample_chat_data["id"]
        mock_chat.__class__.__name__ = "Channel"
        mock_chat.title = sample_chat_data["title"]
        mock_chat.username = sample_chat_data["username"]
        mock_chat.verified = sample_chat_data["is_verified"]
        mock_chat.scam = sample_chat_data["is_scam"]
        mock_chat.fake = sample_chat_data["is_fake"]
        mock_chat.participants_count = sample_chat_data["member_count"]
        
        # Create mock user
        mock_user = MagicMock()
        mock_user.id = sample_user_data["id"]
        mock_user.first_name = sample_user_data["first_name"]
        mock_user.last_name = sample_user_data["last_name"]
        mock_user.username = sample_user_data["username"]
        mock_user.bot = sample_user_data["is_bot"]
        mock_user.verified = sample_user_data["is_verified"]
        mock_user.scam = sample_user_data["is_scam"]
        mock_user.fake = sample_user_data["is_fake"]
        mock_user.premium = sample_user_data["is_premium"]
        
        # Setup async methods
        mock_message.get_chat = AsyncMock(return_value=mock_chat)
        mock_message.get_sender = AsyncMock(return_value=mock_user)
        
        # Run handler
        await new_message_handler(mock_event)
        
        # Verify message was saved
        from sqlalchemy.future import select
        result = await test_session.execute(
            select(Message).where(
                Message.message_id == 123,
                Message.chat_id == sample_chat_data["id"]
            )
        )
        saved_message = result.scalar_one_or_none()
        
        assert saved_message is not None
        assert saved_message.message_id == 123
        assert saved_message.chat_id == sample_chat_data["id"]
        assert saved_message.sender_id == sample_user_data["id"]
    
    @pytest.mark.asyncio
    @patch('jobs.telethon_hook.dependency')
    async def test_message_edited_handler(self, mock_dependency, test_session, sample_chat_data, sample_user_data):
        """Test message edited handler."""
        # Setup mock dependency
        mock_dependency.get_session.return_value.__aiter__.return_value = [test_session]
        
        # Create existing message
        message_data = {
            "message_id": 123,
            "chat_id": sample_chat_data["id"],
            "sender_id": sample_user_data["id"],
            "date": "2024-01-01T12:00:00Z",
            "message_type": "text",
            "is_read": False,
            "is_deleted": False,
            "raw_data": {"id": 123, "message": "Original message"}
        }
        
        message = Message(**message_data)
        test_session.add(message)
        await test_session.commit()
        
        # Create mock event
        mock_event = MagicMock()
        mock_event.chat_id = sample_chat_data["id"]
        mock_event.message = MagicMock()
        mock_event.message.id = 123
        mock_event.message.raw_data = {"id": 123, "message": "Updated message"}
        
        # Run handler
        await message_edited_handler(mock_event)
        
        # Verify message was updated
        from sqlalchemy.future import select
        result = await test_session.execute(
            select(Message).where(
                Message.message_id == 123,
                Message.chat_id == sample_chat_data["id"]
            )
        )
        updated_message = result.scalar_one()
        
        assert updated_message.raw_data["message"] == "Updated message"
    
    @pytest.mark.asyncio
    @patch('jobs.telethon_hook.dependency')
    async def test_message_deleted_handler(self, mock_dependency, test_session, sample_chat_data, sample_user_data):
        """Test message deleted handler."""
        # Setup mock dependency
        mock_dependency.get_session.return_value.__aiter__.return_value = [test_session]
        
        # Create existing messages
        message1_data = {
            "message_id": 123,
            "chat_id": sample_chat_data["id"],
            "sender_id": sample_user_data["id"],
            "date": "2024-01-01T12:00:00Z",
            "message_type": "text",
            "is_read": False,
            "is_deleted": False,
            "raw_data": {"id": 123, "message": "Message 1"}
        }
        
        message2_data = {
            "message_id": 124,
            "chat_id": sample_chat_data["id"],
            "sender_id": sample_user_data["id"],
            "date": "2024-01-01T12:01:00Z",
            "message_type": "text",
            "is_read": False,
            "is_deleted": False,
            "raw_data": {"id": 124, "message": "Message 2"}
        }
        
        message1 = Message(**message1_data)
        message2 = Message(**message2_data)
        test_session.add(message1)
        test_session.add(message2)
        await test_session.commit()
        
        # Create mock event
        mock_event = MagicMock()
        mock_event.chat_id = sample_chat_data["id"]
        mock_event.deleted_ids = [123, 124]
        
        # Run handler
        await message_deleted_handler(mock_event)
        
        # Verify messages were marked as deleted
        from sqlalchemy.future import select
        result = await test_session.execute(
            select(Message).where(
                Message.chat_id == sample_chat_data["id"],
                Message.message_id.in_([123, 124])
            )
        )
        deleted_messages = result.scalars().all()
        
        for message in deleted_messages:
            assert message.is_deleted is True


class TestChatConfigIntegration:
    """Test chat config integration with message processing."""
    
    @pytest.mark.asyncio
    @patch('jobs.telethon_hook.dependency')
    @patch('jobs.telethon_hook.process_message')
    async def test_message_enrichment_enabled(self, mock_process_message, mock_dependency, test_session, sample_chat_data):
        """Test message enrichment when enabled in chat config."""
        # Setup mock dependency
        mock_dependency.get_session.return_value.__aiter__.return_value = [test_session]
        mock_dependency.telegram_client = AsyncMock()
        
        # Create chat and config
        chat = Chat(**sample_chat_data)
        test_session.add(chat)
        await test_session.commit()
        
        chat_config = ChatConfig(
            chat_id=sample_chat_data["id"],
            enrich_messages=True,
            recognize_photo=False
        )
        test_session.add(chat_config)
        await test_session.commit()
        
        # Create mock event
        mock_event = MagicMock()
        mock_message = MagicMock()
        mock_message.id = 123
        mock_message.date = "2024-01-01T12:00:00Z"
        mock_message.media = None
        mock_event.message = mock_message
        
        mock_chat = MagicMock()
        mock_chat.id = sample_chat_data["id"]
        mock_message.get_chat = AsyncMock(return_value=mock_chat)
        mock_message.get_sender = AsyncMock(return_value=None)
        
        # Run handler
        await new_message_handler(mock_event)
        
        # Verify process_message was called
        mock_process_message.assert_called_once_with(
            test_session,
            chat_id=sample_chat_data["id"],
            message_id=123
        )
    
    @pytest.mark.asyncio
    @patch('jobs.telethon_hook.dependency')
    @patch('jobs.telethon_hook.process_message')
    async def test_message_enrichment_disabled(self, mock_process_message, mock_dependency, test_session, sample_chat_data):
        """Test message enrichment when disabled in chat config."""
        # Setup mock dependency
        mock_dependency.get_session.return_value.__aiter__.return_value = [test_session]
        mock_dependency.telegram_client = AsyncMock()
        
        # Create chat and config with enrichment disabled
        chat = Chat(**sample_chat_data)
        test_session.add(chat)
        await test_session.commit()
        
        chat_config = ChatConfig(
            chat_id=sample_chat_data["id"],
            enrich_messages=False,  # Disabled
            recognize_photo=False
        )
        test_session.add(chat_config)
        await test_session.commit()
        
        # Create mock event
        mock_event = MagicMock()
        mock_message = MagicMock()
        mock_message.id = 123
        mock_message.date = "2024-01-01T12:00:00Z"
        mock_message.media = None
        mock_event.message = mock_message
        
        mock_chat = MagicMock()
        mock_chat.id = sample_chat_data["id"]
        mock_message.get_chat = AsyncMock(return_value=mock_chat)
        mock_message.get_sender = AsyncMock(return_value=None)
        
        # Run handler
        await new_message_handler(mock_event)
        
        # Verify process_message was not called
        mock_process_message.assert_not_called() 