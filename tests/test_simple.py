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
