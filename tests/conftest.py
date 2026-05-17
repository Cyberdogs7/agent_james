import pytest
import asyncio
import os
import tempfile
import shutil
import sys
from unittest.mock import MagicMock

# Ensure backend is in path
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock dependencies that might be missing in the environment
mock_modules = [
    'dotenv',
    'cv2',
    'pyaudio',
    'mss',
    'PIL',
    'PIL.Image',
    'google',
    'google.genai',
    'google.genai.types',
    'tzlocal',
    'pydantic',
    'httpx',
    'psutil',
    'numpy',
    'requests',
    'slack_sdk',
    'slack_sdk.web',
    'slack_sdk.web.async_client',
    'slack_sdk.socket_mode',
    'slack_sdk.socket_mode.request',
    'slack_sdk.socket_mode.async_client',
    'slack_sdk.socket_mode.aiohttp',
    'mediapipe',
    'ytmusicapi',
    'yt_dlp',
    'build123d',
    'playwright',
    'playwright.async_api',
    'kasa',
    'zeroconf',
    'aiohttp',
    'beautifulsoup4',
    'bs4',
    'imageio_ffmpeg'
]

for module in mock_modules:
    sys.modules[module] = MagicMock()

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
