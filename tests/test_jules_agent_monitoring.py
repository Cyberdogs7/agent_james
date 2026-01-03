import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from backend.jules_agent import JulesAgent


@pytest.fixture
def jules_agent(monkeypatch):
    """Fixture to create a JulesAgent instance for testing."""
    monkeypatch.setenv("JULES_API_KEY", "test-key")
    return JulesAgent()


@pytest.mark.asyncio
async def test_start_monitoring_detects_state_change(jules_agent):
    """Test that the monitoring loop correctly detects and reports a session state change."""
    # Mock the callback that will be triggered on state change
    mock_status_change_callback = AsyncMock()

    # Define a sequence of responses for the mocked list_sessions
    mock_sessions_responses = [
        # First call: one session in PLANNING state
        [{"name": "sessions/123", "state": "PLANNING", "title": "Test Task"}],
        # Second call: the same session has moved to IN_PROGRESS
        [{"name": "sessions/123", "state": "IN_PROGRESS", "title": "Test Task"}],
        # Third call: session is now COMPLETED (should be ignored and removed)
        [{"name": "sessions/123", "state": "COMPLETED", "title": "Test Task"}],
        # Fourth call: session is gone
        [],
    ]

    with patch.object(jules_agent, "list_sessions", new_callable=AsyncMock) as mock_list_sessions:
        # The monitoring loop runs indefinitely, so we need a way to stop it.
        # We'll patch asyncio.sleep to raise a custom exception after a few calls.
        class StopTest(Exception):
            pass

        original_sleep = asyncio.sleep
        async def sleep_side_effect(*args, **kwargs):
            if mock_list_sessions.call_count >= 4:
                raise StopTest
            await original_sleep(0) # Allow other tasks to run

        with patch("asyncio.sleep", new=sleep_side_effect):
            mock_list_sessions.side_effect = mock_sessions_responses

            try:
                await jules_agent.start_monitoring(mock_status_change_callback)
            except StopTest:
                pass  # Test finished

    # Verification
    # The callback should have been called exactly once for the state change
    mock_status_change_callback.assert_called_once_with("Test Task", "IN_PROGRESS")

    # list_sessions should have been called multiple times
    assert mock_list_sessions.call_count >= 2
