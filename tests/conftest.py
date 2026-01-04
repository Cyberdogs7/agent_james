import pytest
import asyncio
import os
import tempfile
import shutil

@pytest.fixture(autouse=True)
def mock_api_keys(monkeypatch):
    """Mocks API keys for tests."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-api-key")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# If you need to change the scope of the event_loop fixture, you can do so.
# For example, to have a new event loop for each function:
# @pytest.fixture(scope="function")
# def event_loop(request):
#     """Create an instance of the default event loop for each test function."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()

@pytest.fixture(scope="session", autouse=True)
def default_asyncio_loop_scope():
    return "session"

@pytest.fixture
def printers():
    # Example printer data, adjust as needed for your tests
    return [
        {"name": "Prusa MK3", "host": "192.168.1.100", "port": 80, "type": "octoprint", "api_key": "test_api_key_1"},
        {"name": "Voron 2.4", "host": "192.168.1.101", "port": 7125, "type": "moonraker", "api_key": "test_api_key_2"},
    ]

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

@pytest.fixture
def kasa_devices():
    """Mock Kasa devices for testing."""
    # This can be expanded with more realistic mock objects if needed
    return {
        "192.168.1.10": {"alias": "Living Room Lamp", "is_on": False, "is_bulb": True},
        "192.168.1.11": {"alias": "Desk Fan", "is_on": True, "is_plug": True},
    }