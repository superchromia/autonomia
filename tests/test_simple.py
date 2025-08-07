import pytest

def test_basic():
    """Basic test to verify pytest is working."""
    assert True

def test_imports():
    """Test that we can import our modules."""
    try:
        from processing.enrich_message import EnrichedMessageData, format_message
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_format_message():
    """Test the format_message function."""
    from processing.enrich_message import format_message
    
    raw_data = {"id": 123, "message": "Hello world"}
    username = "testuser"
    
    result = format_message(raw_data, username)
    
    assert "Сообщение 123" in result
    assert "testuser" in result
    assert "Hello world" in result

def test_chat_config_model():
    """Test ChatConfig model functionality."""
    try:
        from models.chat_config import ChatConfig
        from models.chat import Chat
        
        # Test that we can create a ChatConfig instance
        config = ChatConfig(
            chat_id=123456789,
            save_messages=True,
            enrich_messages=True,
            recognize_photo=False,
            system_prompt="Test prompt",
            answer_threshold=0.8
        )
        
        assert config.chat_id == 123456789
        assert config.save_messages is True
        assert config.enrich_messages is True
        assert config.recognize_photo is False
        assert config.system_prompt == "Test prompt"
        assert config.answer_threshold == 0.8
        
        # Test string representation
        repr_str = repr(config)
        assert "ChatConfig" in repr_str
        assert "123456789" in repr_str
        
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_chat_config_foreign_key():
    """Test that ChatConfig has proper foreign key relationship."""
    try:
        from models.chat_config import ChatConfig
        from models.chat import Chat
        
        # Check that ChatConfig has foreign key to Chat
        chat_id_column = ChatConfig.__table__.c.chat_id
        assert chat_id_column.foreign_keys is not None
        
        # Check that the foreign key points to chats.id
        for fk in chat_id_column.foreign_keys:
            assert fk.column.table.name == "chats"
            assert fk.column.name == "id"
        
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")
