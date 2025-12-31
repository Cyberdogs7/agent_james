import asyncio
from unittest.mock import AsyncMock, patch
import datetime
import os
import json

import pytest
from backend.timer_agent import TimerAgent

STORAGE_FILE = "test_timers.json"

@pytest.fixture
def timer_agent():
    """Fixture to create a TimerAgent instance for testing."""
    # Clean up the storage file before each test
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)

    # Mock the pyaudio.PyAudio class to avoid audio hardware issues in a headless environment
    with patch('pyaudio.PyAudio') as mock_pyaudio:
        mock_pyaudio.return_value.open.return_value = AsyncMock()
        mock_ada_session = AsyncMock()
        agent = TimerAgent(session=mock_ada_session, storage_file=STORAGE_FILE)
        yield agent

    # Clean up the storage file after each test
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)

def get_future_timestamp(minutes=5):
    """Returns a timestamp string in ISO format for a future time."""
    future_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    return future_time.isoformat(timespec='seconds')

@pytest.mark.anyio
async def test_set_timer(timer_agent):
    """Test setting a timer."""
    duration = 10
    name = "test_timer"
    result = await timer_agent.set_timer(duration, name)
    assert result == f"Timer '{name}' set for {duration} seconds."
    assert name in timer_agent.active_timers
    timer_agent.active_timers[name]["task"].cancel()

@pytest.mark.anyio
async def test_set_reminder(timer_agent):
    """Test setting a reminder."""
    timestamp = get_future_timestamp()
    name = "test_reminder"
    result = await timer_agent.set_reminder(timestamp, name)
    assert f"Reminder '{name}' set for" in result
    assert name in timer_agent.active_reminders
    # Clean up the task to prevent it from running
    timer_agent.active_reminders[name]["task"].cancel()

@pytest.mark.anyio
async def test_list_timers(timer_agent):
    """Test listing active timers and reminders."""
    reminder_timestamp = get_future_timestamp()
    await timer_agent.set_timer(10, "timer1")
    await timer_agent.set_reminder(reminder_timestamp, "reminder1")
    result = timer_agent.list_timers()
    assert "timer1" in result
    assert "reminder1" in result
    # Clean up tasks
    timer_agent.active_timers["timer1"]["task"].cancel()
    timer_agent.active_reminders["reminder1"]["task"].cancel()

@pytest.mark.anyio
async def test_delete_entry(timer_agent):
    """Test deleting a timer."""
    await timer_agent.set_timer(10, "timer1")
    result = timer_agent.delete_entry("timer1")
    assert result == "Timer 'timer1' deleted."
    assert "timer1" not in timer_agent.active_timers

@pytest.mark.anyio
async def test_delete_reminder(timer_agent):
    """Test deleting a reminder."""
    reminder_timestamp = get_future_timestamp()
    await timer_agent.set_reminder(reminder_timestamp, "reminder1")
    result = timer_agent.delete_entry("reminder1")
    assert result == "Reminder 'reminder1' deleted."
    assert "reminder1" not in timer_agent.active_reminders

@pytest.mark.anyio
async def test_modify_timer(timer_agent):
    """Test modifying a timer."""
    await timer_agent.set_timer(10, "timer1")
    result = await timer_agent.modify_timer("timer1", new_duration=20)
    assert result == "Timer 'timer1' modified to 20 seconds."
    assert timer_agent.active_timers["timer1"]["duration"] == 20
    timer_agent.active_timers["timer1"]["task"].cancel()

@pytest.mark.anyio
async def test_modify_reminder(timer_agent):
    """Test modifying a reminder."""
    reminder_timestamp = get_future_timestamp()
    await timer_agent.set_reminder(reminder_timestamp, "reminder1")
    new_timestamp = get_future_timestamp(minutes=10)
    result = await timer_agent.modify_timer("reminder1", new_timestamp=new_timestamp)
    assert f"Reminder 'reminder1' modified to" in result
    assert new_timestamp in timer_agent.active_reminders["reminder1"]["reminder_time"]
    timer_agent.active_reminders["reminder1"]["task"].cancel()

@pytest.mark.anyio
async def test_persistence(timer_agent):
    """Test that timers and reminders are saved to and loaded from disk."""
    await timer_agent.set_timer(10, "timer1")
    await timer_agent.set_reminder(get_future_timestamp(), "reminder1")

    # Create a new agent to load from the same file
    with patch('pyaudio.PyAudio') as mock_pyaudio:
        mock_pyaudio.return_value.open.return_value = AsyncMock()
        new_agent = TimerAgent(session=AsyncMock(), storage_file=STORAGE_FILE)
        assert "timer1" in new_agent.active_timers
        assert "reminder1" in new_agent.active_reminders
        new_agent.active_timers["timer1"]["task"].cancel()
        new_agent.active_reminders["reminder1"]["task"].cancel()
