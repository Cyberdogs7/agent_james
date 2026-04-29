import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import sys
import os

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from automation_engine import AutomationEngine

class TestNaggingSecretary(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.task_manager = MagicMock()
        self.project_manager = MagicMock()
        self.ada = MagicMock()
        self.ada.jules_agent = MagicMock()

        self.engine = AutomationEngine(self.task_manager, self.project_manager, self.ada)

        # Mock handle_external_event as async
        self.ada.handle_external_event = AsyncMock()
        self.ada.jules_agent.list_sessions = AsyncMock()

    async def test_stalled_session_trigger(self):
        # Setup stale session
        stale_time = (datetime.utcnow() - timedelta(hours=3)).isoformat() + 'Z'

        self.ada.jules_agent.list_sessions.return_value = [
            {
                "name": "session/123",
                "title": "Fix Bug",
                "state": "RUNNING",
                "updateTime": stale_time
            }
        ]

        # Disable PR check for this test
        self.project_manager.get_github_token.return_value = None

        # Run
        await self.engine._monitor_stalled_items()

        # Assert
        self.ada.handle_external_event.assert_called_once()
        args, _ = self.ada.handle_external_event.call_args
        event = args[0]
        self.assertEqual(event['type'], 'notification')
        self.assertIn("Fix Bug", event['message'])
        self.assertIn("intervene", event['message'])

    async def test_recent_session_no_trigger(self):
        # Setup recent session
        recent_time = (datetime.utcnow() - timedelta(minutes=30)).isoformat() + 'Z'

        self.ada.jules_agent.list_sessions.return_value = [
            {
                "name": "session/456",
                "title": "Active Task",
                "state": "RUNNING",
                "updateTime": recent_time
            }
        ]

        self.project_manager.get_github_token.return_value = None

        # Run
        await self.engine._monitor_stalled_items()

        # Assert
        self.ada.handle_external_event.assert_not_called()

    @patch('automation_engine.GitHubClient')
    async def test_stalled_pr_trigger(self, MockGitHubClient):
        # Setup PR check
        self.project_manager.get_github_token.return_value = "fake_token"
        self.project_manager.load_fleet.return_value = [{"owner": "me", "name": "my-repo"}]

        import sys
        import types
        sys.modules['backend.server'] = types.ModuleType('backend.server')
        sys.modules['backend.server'].fleet_manager = MagicMock()
        sys.modules['backend.server'].fleet_manager.repos = {"me/my-repo": {"is_active": True}}

        mock_client = MockGitHubClient.return_value
        mock_client.list_pull_requests = AsyncMock()

        stale_time = (datetime.utcnow() - timedelta(hours=3)).isoformat() + 'Z'

        mock_client.list_pull_requests.return_value = [
            {
                "html_url": "http://github.com/me/my-repo/pull/1",
                "title": "Feature X",
                "updated_at": stale_time
            }
        ]

        # No stale sessions
        self.ada.jules_agent.list_sessions.return_value = []

        # Run
        await self.engine._monitor_stalled_items()

        # Assert
        self.ada.handle_external_event.assert_called_once()
        args, _ = self.ada.handle_external_event.call_args
        event = args[0]
        self.assertEqual(event['type'], 'notification')
        self.assertIn("Feature X", event['message'])
        self.assertIn("merge it", event['message'])

if __name__ == '__main__':
    unittest.main()
