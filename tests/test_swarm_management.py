import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.jules_agent import JulesAgent

class TestSwarmManagement(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.agent = JulesAgent(api_key="mock_key")
        # Mock the http client
        self.agent.client = AsyncMock()

    async def test_start_stop_polling(self):
        session_id = "sessions/123"
        callback = MagicMock()

        # Start Polling
        self.agent.start_polling(session_id, callback)

        self.assertIn(session_id, self.agent.polling_tasks)
        task_info = self.agent.polling_tasks[session_id]
        self.assertIsInstance(task_info["task"], asyncio.Task)
        self.assertFalse(task_info["stop_event"].is_set())

        # Stop Polling
        self.agent.stop_polling(session_id)

        # Allow the task to clean up (it awaits removing itself)
        # But wait, stop_polling pops it immediately.
        self.assertNotIn(session_id, self.agent.polling_tasks)
        self.assertTrue(task_info["stop_event"].is_set())

        # Clean up task to avoid "Task was destroyed but it is pending!" warning
        try:
            await task_info["task"]
        except asyncio.CancelledError:
            pass

    async def test_poll_loop_execution(self):
        # We need to test that the poll loop calls the callback
        session_id = "sessions/test_callback"

        # Mock list_activities to return some data
        mock_activities = {
            "activities": [
                {"agentMessage": {"content": "Hello World"}}
            ]
        }
        self.agent.list_activities = AsyncMock(return_value=mock_activities)

        callback_future = asyncio.Future()

        def callback(msg):
            if not callback_future.done():
                callback_future.set_result(msg)

        # Start Polling
        self.agent.start_polling(session_id, callback)

        try:
            # Wait for callback
            result = await asyncio.wait_for(callback_future, timeout=2.0)
            self.assertIn("Hello World", result)
        finally:
            self.agent.stop_polling(session_id)
            # Cleanup
            if session_id in self.agent.polling_tasks:
                 await self.agent.polling_tasks[session_id]["task"]

if __name__ == "__main__":
    unittest.main()
