import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from slack_sdk.socket_mode.request import SocketModeRequest

from backend.slack_agent import SlackAgent


@pytest.mark.asyncio
async def test_send_message_sends_message_to_slack(monkeypatch):
    """Verify that the SlackAgent sends a message to the Slack API."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "test_channel_id")
    monkeypatch.setenv("SLACK_APP_TOKEN", "test_app_token")

    agent = SlackAgent()
    agent.client = AsyncMock()
    await agent.send_message("test message")
    agent.client.chat_postMessage.assert_called_once_with(
        channel="test_channel_id", text="test message"
    )


@pytest.mark.asyncio
async def test_handle_message_calls_on_message_callback(monkeypatch):
    """Verify that the on_message callback is called when the agent is mentioned."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("SLACK_APP_TOKEN", "test_app_token")

    on_message = AsyncMock()
    agent = SlackAgent(on_message=on_message)
    agent.user_id = "U12345"

    mock_client = AsyncMock()
    req = SocketModeRequest(
        type="events_api",
        envelope_id="test_envelope_id",
        payload={
            "event": {
                "type": "app_mention",
                "text": "<@U12345> test message",
                "user": "U67890",
            }
        },
    )
    await agent._handle_message(mock_client, req)

    mock_client.send_socket_mode_response.assert_called_once_with("test_envelope_id")
    on_message.assert_called_once_with("test message")
