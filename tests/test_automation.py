import unittest
from unittest.mock import MagicMock, patch
import json
import os
import shutil
import time
import asyncio
from backend.task_manager import TaskManager
from backend.automation_engine import AutomationEngine

class TestAutomation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = "tests/temp_project"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
        self.task_manager = TaskManager(self.test_dir)

        # Mock ProjectManager
        self.mock_pm = MagicMock()
        # Mocking get_current_project_path to return a Path object, as TaskManager expects it (or string is fine usually)
        # But my code uses `Path(project_path)` so string is fine.
        self.mock_pm.get_current_project_path.return_value = self.test_dir

        self.engine = AutomationEngine(self.task_manager, self.mock_pm)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_schedule_validation(self):
        # Valid
        self.assertTrue(self.task_manager.validate_schedule({"mode": "interval", "interval_minutes": 30}))
        self.assertTrue(self.task_manager.validate_schedule({"mode": "daily", "time": "14:00"}))

        # Invalid
        with self.assertRaises(ValueError):
            self.task_manager.validate_schedule({"mode": "interval"}) # Missing min
        with self.assertRaises(ValueError):
            self.task_manager.validate_schedule({"mode": "daily", "time": "25:00"}) # Bad time

    async def test_interval_trigger(self):
        # Create task running every 10 mins
        task = self.task_manager.create_task(
            "Test Interval",
            trigger_type="schedule",
            trigger_value={"mode": "interval", "interval_minutes": 10},
            action_type="run_script",
            action_value="echo hello"
        )

        # Mock time
        with patch('backend.automation_engine.time.time') as mock_time:
            # Set initial time
            start_time = 1000000
            mock_time.return_value = start_time

            # We need to mock _execute_task to track calls
            # Since _execute_task is an async method, we mock it with an async side effect or Future
            original_execute = self.engine._execute_task
            self.engine._execute_task = MagicMock()
            f = asyncio.Future()
            f.set_result(None)
            self.engine._execute_task.return_value = f

            # 1. First run (never ran) -> Should run
            await self.engine._check_schedules()
            self.engine._execute_task.assert_called()

            # Manually update task last_run since we mocked execute (which usually updates it)
            self.task_manager.update_task(task['id'], {"last_run": start_time})

            # Reset mock
            self.engine._execute_task.reset_mock()
            f = asyncio.Future()
            f.set_result(None)
            self.engine._execute_task.return_value = f

            # 2. Check 1 min later -> Should NOT run
            mock_time.return_value = start_time + 60
            await self.engine._check_schedules()
            self.engine._execute_task.assert_not_called()

            # 3. Check 11 mins later -> Should Run
            mock_time.return_value = start_time + (11 * 60)
            await self.engine._check_schedules()
            self.engine._execute_task.assert_called()

    async def test_git_trigger(self):
        task = self.task_manager.create_task(
            "Test Git",
            trigger_type="git",
            trigger_value="owner/repo",
            action_type="notify",
            action_value="Commit detected"
        )

        # Mock execute
        self.engine._execute_task = MagicMock()
        f = asyncio.Future()
        f.set_result(None)
        self.engine._execute_task.return_value = f

        # Trigger event
        await self.engine.trigger_event("git_commit", {"repo": "owner/repo", "message": "fix"})

        self.engine._execute_task.assert_called()

        # Trigger mismatch
        self.engine._execute_task.reset_mock()
        f = asyncio.Future()
        f.set_result(None)
        self.engine._execute_task.return_value = f

        await self.engine.trigger_event("git_commit", {"repo": "other/repo", "message": "fix"})
        self.engine._execute_task.assert_not_called()

if __name__ == '__main__':
    unittest.main()
