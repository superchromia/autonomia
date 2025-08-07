import pytest
import json
from unittest.mock import Mock

from processing.enrich_message import EnrichedMessageData, format_message


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
    
    def test_format_message_without_reply(self):
        """Test message formatting without reply."""
        raw_data = {
            "id": 125,
            "message": "Simple message"
        }
        username = "testuser"
        
        result = format_message(raw_data, username)
        
        assert "Сообщение 125" in result
        assert "testuser" in result
        assert "Simple message" in result
        assert "id=" not in result


class TestUtils:
    """Test utility functions."""
    
    def test_json_serialization(self):
        """Test JSON serialization of EnrichedMessageData."""
        data = EnrichedMessageData(
            context="Test context",
            meaning="Test meaning"
        )
        
        json_str = data.model_dump_json()
        parsed_data = json.loads(json_str)
        
        assert parsed_data["context"] == "Test context"
        assert parsed_data["meaning"] == "Test meaning"
    
    def test_mock_objects(self):
        """Test creating mock objects for testing."""
        mock_chat = Mock()
        mock_chat.id = 123456789
        mock_chat.title = "Test Channel"
        mock_chat.username = "testchannel"
        mock_chat.verified = False
        mock_chat.scam = False
        mock_chat.fake = False
        mock_chat.participants_count = 1000
        
        assert mock_chat.id == 123456789
        assert mock_chat.title == "Test Channel"
        assert mock_chat.username == "testchannel"
        assert mock_chat.verified is False
        assert mock_chat.scam is False
        assert mock_chat.fake is False
        assert mock_chat.participants_count == 1000


class TestStringOperations:
    """Test string operations used in the application."""
    
    def test_string_formatting(self):
        """Test string formatting operations."""
        chat_id = 123456789
        message_id = 111
        username = "testuser"
        message_text = "Hello world"
        
        formatted = f"Chat {chat_id}, Message {message_id}: @{username} says '{message_text}'"
        
        assert str(chat_id) in formatted
        assert str(message_id) in formatted
        assert username in formatted
        assert message_text in formatted
    
    def test_string_concatenation(self):
        """Test string concatenation operations."""
        parts = [
            "Chat ID: 123456789",
            "Message ID: 111",
            "User: testuser",
            "Text: Hello world"
        ]
        
        result = " | ".join(parts)
        
        assert "Chat ID: 123456789" in result
        assert "Message ID: 111" in result
        assert "User: testuser" in result
        assert "Text: Hello world" in result
        assert result.count(" | ") == 3 