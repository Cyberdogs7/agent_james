import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from backend.proactive_agent import ProactiveAgent

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.send = AsyncMock()
    return session

@pytest.fixture
def mock_project_manager():
    pm = MagicMock()
    pm.current_project = "Project_A"
    return pm

@pytest.fixture
def proactive_agent(mock_session, mock_project_manager):
    return ProactiveAgent(
        session=mock_session,
        project_manager=mock_project_manager,
        suggestion_interval=300
    )

@pytest.mark.asyncio
async def test_check_context_switch_with_git_suggestion(proactive_agent):
    # Mock _analyze_screen
    proactive_agent._analyze_screen = AsyncMock(return_value={"project": "Project_B"})

    suggestion = await proactive_agent._check_context_switch()

    assert "Project_B" in suggestion
    assert "git status" in suggestion

@pytest.mark.asyncio
async def test_make_suggestion_format(proactive_agent, mock_session):
    await proactive_agent._make_suggestion("Test suggestion")

    # Verify the call format
    args, kwargs = mock_session.send.call_args
    assert kwargs['input'] == "System Notification: Test suggestion"
    assert kwargs['end_of_turn'] is True
