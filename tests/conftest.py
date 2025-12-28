import pytest
import asyncio
import os

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
