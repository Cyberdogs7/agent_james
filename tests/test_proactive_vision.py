import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import sys
import os
import json

# Ensure backend can be imported
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.proactive_agent import ProactiveAgent


def _llm_vision_mock(payload):
    mock_llm = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = json.dumps(payload)
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_llm.chat_completion = AsyncMock(return_value=mock_resp)
    return mock_llm

@pytest.mark.asyncio
async def test_analyze_screen():
    # Setup Mocks
    mock_session = AsyncMock()
    mock_pm = MagicMock()
    mock_pm.current_project = "ProjectA"

    mock_llm = _llm_vision_mock({
        "app": "vscode",
        "project": "ProjectB",
        "file": "main.py",
        "repo": "owner/repo"
    })

    mock_vision = MagicMock()
    mock_vision.return_value = {"mime_type": "image/jpeg", "data": "base64data"}

    # Instantiate Agent
    agent = ProactiveAgent(
        session=mock_session,
        project_manager=mock_pm,
        vision_provider=mock_vision,
        llm_client=mock_llm
    )

    # Run Analysis
    result = await agent._analyze_screen()

    # Verify
    assert result is not None
    assert result["project"] == "ProjectB"
    assert mock_llm.chat_completion.called

@pytest.mark.asyncio
async def test_check_context_switch_triggers():
    # Setup Mocks
    mock_session = AsyncMock()
    mock_pm = MagicMock()
    mock_pm.current_project = "ProjectA"

    mock_llm = _llm_vision_mock({
        "app": "vscode",
        "project": "ProjectB",
        "file": "main.py",
        "repo": "owner/repo"
    })

    mock_vision = MagicMock()
    mock_vision.return_value = {"mime_type": "image/jpeg", "data": "base64data"}

    agent = ProactiveAgent(
        session=mock_session,
        project_manager=mock_pm,
        vision_provider=mock_vision,
        llm_client=mock_llm
    )

    # Run Check
    suggestion = await agent._check_context_switch()

    # Verify Suggestion
    assert suggestion is not None
    assert "ProjectB" in suggestion
    assert "switch" in suggestion

@pytest.mark.asyncio
async def test_check_context_switch_no_trigger_same_project():
    # Setup Mocks
    mock_session = AsyncMock()
    mock_pm = MagicMock()
    mock_pm.current_project = "ProjectA"

    mock_llm = _llm_vision_mock({
        "app": "vscode",
        "project": "ProjectA",
        "file": "main.py",
        "repo": "owner/repo"
    })

    mock_vision = MagicMock()
    mock_vision.return_value = {"mime_type": "image/jpeg", "data": "base64data"}

    agent = ProactiveAgent(
        session=mock_session,
        project_manager=mock_pm,
        vision_provider=mock_vision,
        llm_client=mock_llm
    )

    # Run Check
    suggestion = await agent._check_context_switch()

    # Verify No Suggestion
    assert suggestion is None
