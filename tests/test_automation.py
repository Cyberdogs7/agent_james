import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import time
import sys
import os

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.automation_engine import AutomationEngine

class TestAutomationEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_pm = MagicMock()
        self.mock_pm.get_current_project_path.return_value = "/tmp/test_project"
        # monitor_git_repos needs to be awaitable
        self.mock_pm.monitor_git_repos = AsyncMock(return_value=[])

        self.mock_tm = MagicMock()
        self.mock_tm.list_tasks.return_value = []

        # Mock class for TaskManager so engine can "instantiate" it
        self.mock_tm_cls = MagicMock(return_value=self.mock_tm)

        self.engine = AutomationEngine(
            project_manager=self.mock_pm,
            task_manager=self.mock_tm, # Passed as instance, converted to class in init
        )
        # Fix the mock class injection because we passed a mock instance which has no __class__ we control easily
        self.engine.task_manager_cls = self.mock_tm_cls

    def test_schedule_interval(self):
        # Create a task that ran 11 mins ago
        now = time.time()
        last_run = now - (11 * 60)

        task = {
            "id": "1",
            "trigger": {"type": "schedule", "value": "10m"},
            "last_run": last_run,
            "created_at": last_run
        }

        # Should trigger
        self.assertTrue(self.engine._check_schedule(task))

        # Create a task that ran 5 mins ago
        task['last_run'] = now - (5 * 60)
        self.assertFalse(self.engine._check_schedule(task))

    async def test_execution_flow(self):
        # Async test
        task = {
            "id": "1",
            "title": "Test Task",
            "status": "active",
            "trigger": {"type": "schedule", "value": "10m"},
            "action": {"type": "notify", "value": "Hello"},
            "last_run": 0
        }

        self.mock_tm.list_tasks.return_value = [task]

        # Mock _check_schedule to return True
        self.engine._check_schedule = MagicMock(return_value=True)

        # Run check_triggers
        triggered = await self.engine.check_triggers()

        self.assertTrue(triggered)
        # Check if notification queued
        self.assertFalse(self.engine.notification_queue.empty())
        msg = self.engine.get_pending_notifications()[0]
        self.assertIn("Hello", msg)

        # Check if save was called
        self.mock_tm.save_tasks.assert_called()

if __name__ == '__main__':
    unittest.main()
