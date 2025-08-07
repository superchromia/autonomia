import json
import pytest
from unittest.mock import AsyncMock, patch

from processing.enrich_message import (
    EnrichedMessageData,
    format_message,
    collect_message_context,
    process_message
)
from models.chat import Chat
from models.message import Message
from models.user import User
from models.messages_enriched import EnrichedMessage


class TestEnrichedMessageData:
    """Test EnrichedMessageData Pydantic model."""
    
    def test_enriched_message_data_creation(self):
        """Test creating EnrichedMessageData instance."""
        data = EnrichedMessageData(
            context="Test context",
            meaning="Test meaning"
        )
        
        assert data.context == "Test context"
        assert data.meaning == "Test meaning"
    
    def test_enriched_message_data_json_schema(self):
        """Test JSON schema generation."""
        schema = EnrichedMessageData.model_json_schema()
        
        assert "properties" in schema
        assert "context" in schema["properties"]
        assert "meaning" in schema["properties"]


class TestFormatMessage:
    """Test message formatting functionality."""
    
    def test_format_message_basic(self):
        """Test basic message formatting."""
        raw_data = {
            "id": 123,
            "message": "Hello world"
        }
        username = "testuser"
        
        result = format_message(raw_data, username)
        
        assert "Сообщение 123" in result
        assert "testuser" in result
        assert "Hello world" in result
    
    def test_format_message_with_reply(self):
        """Test message formatting with reply."""
        raw_data = {
            "id": 124,
            "message": "Reply message",
            "reply_to": {
                "reply_to_msg_id": 123
            }
        }
        username = "testuser"
        
        result = format_message(raw_data, username)
        
        assert "Сообщение 124" in result
        assert "testuser" in result
        assert "Reply message" in result
        assert "id=123" in result


class TestCollectMessageContext:
    """Test message context collection."""
    
    @pytest.mark.asyncio
    async def test_collect_message_context_message_not_found(self, test_session):
        """Test context collection when message not found."""
        result = await collect_message_context(test_session, chat_id=999, message_id=999)
        
        assert result == "Message not found"
    
    @pytest.mark.asyncio
    async def test_collect_message_context_with_messages(self, test_session, sample_chat_data, sample_user_data):
        """Test context collection with existing messages."""
        # Create chat and user
        chat = Chat(**sample_chat_data)
        user = User(**sample_user_data)
        test_session.add(chat)
        test_session.add(user)
        await test_session.commit()
        
        # Create messages
        message1_data = {
            "message_id": 100,
            "chat_id": sample_chat_data["id"],
            "sender_id": sample_user_data["id"],
            "date": "2024-01-01T12:00:00Z",
            "message_type": "text",
            "is_read": False,
            "is_deleted": False,
            "raw_data": {
                "id": 100,
                "message": "First message"
            }
        }
        
        message2_data = {
            "message_id": 101,
            "chat_id": sample_chat_data["id"],
            "sender_id": sample_user_data["id"],
            "date": "2024-01-01T12:01:00Z",
            "message_type": "text",
            "is_read": False,
            "is_deleted": False,
            "raw_data": {
                "id": 101,
                "message": "Second message"
            }
        }
        
        message1 = Message(**message1_data)
        message2 = Message(**message2_data)
        test_session.add(message1)
        test_session.add(message2)
        await test_session.commit()
        
        # Test context collection
        result = await collect_message_context(test_session, chat_id=sample_chat_data["id"], message_id=101)
        
        assert "ПРЕДЫДУЩИЕ СООБЩЕНИЯ:" in result
        assert "ТЕКУЩЕЕ СООБЩЕНИЕ:" in result
        assert "First message" in result
        assert "Second message" in result


class TestProcessMessage:
    """Test message processing functionality."""
    
    @pytest.mark.asyncio
    @patch('processing.enrich_message.ai_client')
    async def test_process_message_success(self, mock_ai_client, test_session, sample_chat_data, sample_user_data):
        """Test successful message processing."""
        # Setup mock AI client
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = '{"context": "test context", "meaning": "test meaning"}'
        
        mock_embeddings_response = AsyncMock()
        mock_embeddings_response.data = [AsyncMock()]
        mock_embeddings_response.data[0].embedding = [0.1] * 4096
        
        mock_ai_client.chat.completions.create.return_value = mock_response
        mock_ai_client.embeddings.create.return_value = mock_embeddings_response
        
        # Create chat and user
        chat = Chat(**sample_chat_data)
        user = User(**sample_user_data)
        test_session.add(chat)
        test_session.add(user)
        await test_session.commit()
        
        # Create message
        message_data = {
            "message_id": 100,
            "chat_id": sample_chat_data["id"],
            "sender_id": sample_user_data["id"],
            "date": "2024-01-01T12:00:00Z",
            "message_type": "text",
            "is_read": False,
            "is_deleted": False,
            "raw_data": {
                "id": 100,
                "message": "Test message"
            }
        }
        
        message = Message(**message_data)
        test_session.add(message)
        await test_session.commit()
        
        # Process message
        result = await process_message(test_session, chat_id=sample_chat_data["id"], message_id=100)
        
        # Verify enriched message was created
        from sqlalchemy.future import select
        result_query = await test_session.execute(
            select(EnrichedMessage).where(
                EnrichedMessage.chat_id == sample_chat_data["id"],
                EnrichedMessage.message_id == 100
            )
        )
        enriched_message = result_query.scalar_one_or_none()
        
        assert enriched_message is not None
        assert enriched_message.context == "test context"
        assert enriched_message.meaning == "test meaning"
        assert len(enriched_message.embeddings) == 4096
    
    @pytest.mark.asyncio
    @patch('processing.enrich_message.ai_client')
    async def test_process_message_ai_error(self, mock_ai_client, test_session, sample_chat_data, sample_user_data):
        """Test message processing with AI client error."""
        # Setup mock AI client to raise exception
        mock_ai_client.chat.completions.create.side_effect = Exception("AI API error")
        
        # Create chat and user
        chat = Chat(**sample_chat_data)
        user = User(**sample_user_data)
        test_session.add(chat)
        test_session.add(user)
        await test_session.commit()
        
        # Create message
        message_data = {
            "message_id": 100,
            "chat_id": sample_chat_data["id"],
            "sender_id": sample_user_data["id"],
            "date": "2024-01-01T12:00:00Z",
            "message_type": "text",
            "is_read": False,
            "is_deleted": False,
            "raw_data": {
                "id": 100,
                "message": "Test message"
            }
        }
        
        message = Message(**message_data)
        test_session.add(message)
        await test_session.commit()
        
        # Process message should raise exception
        with pytest.raises(Exception):
            await process_message(test_session, chat_id=sample_chat_data["id"], message_id=100) 