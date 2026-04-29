import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import time
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from automation_engine import AutomationEngine

class TestSmartMerge(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_pm = MagicMock()
        self.mock_task_manager = MagicMock()
        self.mock_ada = AsyncMock()

        self.engine = AutomationEngine(self.mock_task_manager, self.mock_pm, self.mock_ada)

        # Default mock config
        self.mock_pm.get_project_config.return_value = {}
        self.mock_pm.get_github_token.return_value = "fake_token"
        self.mock_pm.load_fleet.return_value = [{"owner": "test", "name": "repo", "auto_merge_enabled": True}]

    @patch("automation_engine.GitHubClient")
    @patch.dict("sys.modules", {"backend.server": MagicMock()})
    async def test_smart_merge_trigger(self, MockGitHubClient):
        import sys
        sys.modules["backend.server"].fleet_manager.repos = {"test/repo": {"is_active": True}}
        sys.modules["backend.server"].SETTINGS = {}
        # Setup GitHub Client Mock
        mock_client = MockGitHubClient.return_value

        # 1. Mock List PRs
        now = datetime.utcnow()
        old_enough_date = (now - timedelta(hours=3)).isoformat() + "Z" # 3 hours old

        mock_client.list_pull_requests = AsyncMock(return_value=[{
            "number": 123,
            "title": "Fix bug",
            "html_url": "http://github.com/test/repo/pull/123",
            "created_at": old_enough_date,
            "head": {"sha": "abc1234"}
        }])

        # 2. Mock Full PR (Mergeable)
        mock_client.get_pull_request = AsyncMock(return_value={
            "mergeable": True,
            "head": {"sha": "abc1234"}
        })

        # 3. Mock Commit Status (Success)
        mock_client.get_commit_status = AsyncMock(return_value={"state": "success"})

        # 4. Mock Check Runs (Empty/None means trust status)
        mock_client.get_check_runs = AsyncMock(return_value={"check_runs": []})

        # Execute
        await self.engine._monitor_merge_candidates()

        # Verify
        self.mock_ada.handle_external_event.assert_called_once()
        args = self.mock_ada.handle_external_event.call_args[0][0]
        self.assertEqual(args['type'], 'notification')
        self.assertIn("Shall I merge it", args['message'])

    @patch("automation_engine.GitHubClient")
    @patch.dict("sys.modules", {"backend.server": MagicMock()})
    async def test_smart_merge_respects_threshold_config(self, MockGitHubClient):
        import sys
        sys.modules["backend.server"].fleet_manager.repos = {"test/repo": {"is_active": True}}
        sys.modules["backend.server"].SETTINGS = {}
        mock_client = MockGitHubClient.return_value

        # Set config to 5 hours (18000 seconds)
        self.mock_pm.get_project_config.return_value = {"auto_merge_threshold": 18000}

        # PR is 3 hours old (should be ignored now)
        now = datetime.utcnow()
        three_hours_ago = (now - timedelta(hours=3)).isoformat() + "Z"

        mock_client.list_pull_requests = AsyncMock(return_value=[{
            "number": 123,
            "title": "Fix bug",
            "html_url": "http://github.com/test/repo/pull/123",
            "created_at": three_hours_ago
        }])

        await self.engine._monitor_merge_candidates()

        # Verify NO call
        self.mock_ada.handle_external_event.assert_not_called()

    @patch("automation_engine.GitHubClient")
    @patch.dict("sys.modules", {"backend.server": MagicMock()})
    async def test_smart_merge_respects_threshold_default(self, MockGitHubClient):
        import sys
        sys.modules["backend.server"].fleet_manager.repos = {"test/repo": {"is_active": True}}
        sys.modules["backend.server"].SETTINGS = {}
        mock_client = MockGitHubClient.return_value

        # Default is 2 hours. PR is 3 hours old. Should trigger.
        self.mock_pm.get_project_config.return_value = {} # Empty config

        now = datetime.utcnow()
        three_hours_ago = (now - timedelta(hours=3)).isoformat() + "Z"

        mock_client.list_pull_requests = AsyncMock(return_value=[{
            "number": 123,
            "title": "Fix bug",
            "html_url": "http://github.com/test/repo/pull/123",
            "created_at": three_hours_ago,
            "head": {"sha": "abc"}
        }])

        # Mock Green
        mock_client.get_pull_request = AsyncMock(return_value={"mergeable": True, "head": {"sha": "abc"}})
        mock_client.get_commit_status = AsyncMock(return_value={"state": "success"})
        mock_client.get_check_runs = AsyncMock(return_value={"check_runs": []})

        await self.engine._monitor_merge_candidates()

        self.mock_ada.handle_external_event.assert_called()

if __name__ == '__main__':
    unittest.main()
