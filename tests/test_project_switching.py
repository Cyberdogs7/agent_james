import os
import sys
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import shutil

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from google.genai import types

class TestProjectSwitching(unittest.TestCase):
    def setUp(self):
        # Clean up created projects directory before each test
        projects_dir = 'projects'
        if os.path.exists(projects_dir):
            shutil.rmtree(projects_dir)

        # Set a dummy API key to avoid errors during genai.Client initialization
        os.environ['GEMINI_API_KEY'] = 'test_key'

        from ada import AudioLoop
        self.audio_loop = AudioLoop()

    def tearDown(self):
        # Unset the dummy API key
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']

        # Clean up created projects directory after each test
        projects_dir = 'projects'
        if os.path.exists(projects_dir):
            shutil.rmtree(projects_dir)

    @patch('ada.AudioLoop.reconnect')
    def test_switch_project_tool_triggers_reconnect(self, mock_reconnect):
        # Create a mock tool call for switch_project
        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [
            types.FunctionCall(name='switch_project', args={'name': 'TestProject'})
        ]

        # Create a new project for the test to switch to
        self.audio_loop.project_manager.create_project('TestProject')

        # Mock the session object
        self.audio_loop.session = MagicMock()
        self.audio_loop.session.send_tool_response = AsyncMock()

        # Run the tool call handler
        asyncio.run(self.audio_loop._handle_tool_calls(mock_tool_call))

        # Assert that reconnect was called
        mock_reconnect.assert_called_once()

    @patch('ada.AudioLoop.reconnect')
    def test_create_project_tool_triggers_reconnect(self, mock_reconnect):
        # Create a mock tool call for create_project
        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [
            types.FunctionCall(name='create_project', args={'name': 'TestProject'})
        ]

        # Mock the session object
        self.audio_loop.session = MagicMock()
        self.audio_loop.session.send_tool_response = AsyncMock()

        # Run the tool call handler
        asyncio.run(self.audio_loop._handle_tool_calls(mock_tool_call))

        # Assert that reconnect was called
        mock_reconnect.assert_called_once()

if __name__ == '__main__':
    unittest.main()
