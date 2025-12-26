import asyncio
import os
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from backend.jules_agent import JulesAgent


@pytest.fixture
def jules_agent():
    """Fixture to create a JulesAgent instance for testing."""
    # Mock the session object that would be passed from ada.py
    mock_ada_session = AsyncMock()
    # Set the GINI_API_KEY for the test environment
    os.environ["JULES_API_KEY"] = "test_api_key"
    agent = JulesAgent(session=mock_ada_session)
    return agent


@pytest.mark.asyncio
async def test_create_session_success(jules_agent):
    """Test successful creation of a Jules session."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"name": "sessions/test_session_id", "state": "CREATING"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        prompt = "test prompt"
        source = "github.com/test/repo"
        session = await jules_agent.create_session(prompt, source)

        assert session is not None
        assert session["name"] == "sessions/test_session_id"
        assert jules_agent.session_id == "sessions/test_session_id"
        assert "sessions/test_session_id" in jules_agent.active_sessions
        mock_request.assert_called_once()
        call_args = mock_request.call_args.kwargs
        assert call_args["json"]["prompt"] == prompt
        assert call_args["json"]["sourceContext"]["githubRepoContext"]["startingBranch"] == "main"


@pytest.mark.asyncio
async def test_create_session_failure(jules_agent):
    """Test failure case for creating a Jules session."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        # Configure the mock to raise an HTTPStatusError
        mock_request.side_effect = httpx.HTTPStatusError("API Error", request=MagicMock(), response=MagicMock(status_code=500))

        session = await jules_agent.create_session("test prompt", "github.com/test/repo")
        assert session is None


@pytest.mark.asyncio
async def test_send_message_success(jules_agent):
    """Test successfully sending a message to a session."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "message sent"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        response = await jules_agent.send_message("sessions/test_session", "hello")
        assert response["status"] == "message sent"
        mock_request.assert_called_once_with(
            "POST",
            f"{jules_agent.base_url}/sessions/test_session:sendMessage",
            json={"prompt": "hello"},
        )


@pytest.mark.asyncio
async def test_list_sessions_success(jules_agent):
    """Test successfully listing all sessions."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"sessions": [{"name": "session1"}, {"name": "session2"}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        response = await jules_agent.list_sessions()
        assert len(response["sessions"]) == 2
        mock_request.assert_called_once_with("GET", f"{jules_agent.base_url}/sessions")


@pytest.mark.asyncio
async def test_list_sources_success(jules_agent):
    """Test successfully listing all sources."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"sources": [{"name": "source1"}, {"name": "source2"}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        response = await jules_agent.list_sources()
        assert len(response["sources"]) == 2
        mock_request.assert_called_once_with("GET", f"{jules_agent.base_url}/sources")


@pytest.mark.asyncio
async def test_list_activities_success(jules_agent):
    """Test successfully listing activities for a session."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"activities": [{"id": "act1"}, {"id": "act2"}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_response) as mock_request:
        response = await jules_agent.list_activities("sessions/test_session")
        assert len(response["activities"]) == 2
        mock_request.assert_called_once_with("GET", f"{jules_agent.base_url}/sessions/test_session/activities")


@pytest.mark.asyncio
async def test_request_retry_on_429(jules_agent):
    """Test that _request retries on 429 error."""
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429
    mock_response_429.raise_for_status.side_effect = httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=mock_response_429)

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {"success": True}
    mock_response_200.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        
        mock_request.side_effect = [mock_response_429, mock_response_200]
        
        response = await jules_agent._request("GET", "http://test")
        
        assert response == {"success": True}
        assert mock_request.call_count == 2
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_once_with(1) # base_delay * (2 ** 0)


@pytest.mark.asyncio
async def test_poll_for_updates_flow(jules_agent):
    """Test the polling logic for different activity types."""
    session_id = "sessions/test_session"

    # Mock list_activities to return a sequence of responses
    mock_activities_responses = [
        # 1. First poll, one "plan" activity
        {"activities": [{"plan": {"title": "Test Plan"}}]},
        # 2. Second poll, adds a feedback request
        {"activities": [{"plan": {"title": "Test Plan"}}, {"agentMessage": {"content": "I need some feedback."}}]},
        # 3. Third poll, adds a session complete message
        {"activities": [
            {"plan": {"title": "Test Plan"}},
            {"agentMessage": {"content": "I need some feedback."}},
            {"sessionComplete": {}}
        ]},
        # 4. Subsequent polls (should not happen as polling stops)
        {"activities": []}
    ]

    with patch.object(jules_agent, "list_activities", new_callable=AsyncMock) as mock_list_activities, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        # Set up the side effect to cycle through our responses
        mock_list_activities.side_effect = mock_activities_responses

        # We can now await the polling function directly, and it will complete quickly
        try:
            await jules_agent.poll_for_updates(session_id)
        except StopAsyncIteration:
            # This is expected when the side_effect is exhausted
            pass

        # Check calls to ada_session.send
        send_calls = jules_agent.session.send.call_args_list
        assert len(send_calls) == 3

        # Call 1: Plan generated
        assert "Jules has generated a plan." in send_calls[0].kwargs["input"]

        # Call 2: Feedback request
        assert f"Jules is asking for feedback on session {session_id}" in send_calls[1].kwargs["input"]

        # Call 3: Session complete
        assert "Jules has completed the session." in send_calls[2].kwargs["input"]


@pytest.mark.asyncio
async def test_start_persistent_polling(jules_agent):
    """Test that persistent polling discovers new sessions and starts polling them."""

    # Mock list_sessions to return a new session on the first call
    mock_list_sessions_responses = [
        {"sessions": [{"name": "sessions/new_session_1"}]},
        # Return an empty list on subsequent calls to stop the loop for the test
        {"sessions": []}
    ]

    with patch.object(jules_agent, "list_sessions", new_callable=AsyncMock) as mock_list_sessions, \
         patch.object(jules_agent, "poll_for_updates", new_callable=AsyncMock) as mock_poll:

        mock_list_sessions.side_effect = mock_list_sessions_responses

        # We need to run the task and cancel it after it has had a chance to run
        persistent_poll_task = asyncio.create_task(jules_agent.start_persistent_polling())

        await asyncio.sleep(0.1) # Let it run once

        # Check that poll_for_updates was called for the new session
        mock_poll.assert_called_once_with("sessions/new_session_1")
        assert "sessions/new_session_1" in jules_agent.active_sessions

        # Stop the task
        persistent_poll_task.cancel()
        try:
            await persistent_poll_task
        except asyncio.CancelledError:
            pass
