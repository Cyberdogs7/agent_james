import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import sys
import os
import json

# Ensure backend can be imported
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock dependencies
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()

from backend.proactive_agent import ProactiveAgent

@pytest.mark.asyncio
async def test_analyze_screen():
    # Setup Mocks
    mock_session = AsyncMock()
    mock_pm = MagicMock()
    mock_pm.current_project = "ProjectA"

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock()

    # Mock Response
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "app": "vscode",
        "project": "ProjectB",
        "file": "main.py",
        "repo": "owner/repo"
    })
    mock_client.aio.models.generate_content.return_value = mock_response

    mock_vision = MagicMock()
    mock_vision.return_value = {"mime_type": "image/jpeg", "data": "base64data"}

    # Instantiate Agent
    agent = ProactiveAgent(
        session=mock_session,
        project_manager=mock_pm,
        vision_provider=mock_vision,
        genai_client=mock_client
    )

    # Run Analysis
    result = await agent._analyze_screen()

    # Verify
    assert result is not None
    assert result["project"] == "ProjectB"
    assert mock_client.aio.models.generate_content.called

@pytest.mark.asyncio
async def test_check_context_switch_triggers():
    # Setup Mocks
    mock_session = AsyncMock()
    mock_pm = MagicMock()
    mock_pm.current_project = "ProjectA"

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock()

    # Mock Response (Different Project)
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "app": "vscode",
        "project": "ProjectB",
        "file": "main.py",
        "repo": "owner/repo"
    })
    mock_client.aio.models.generate_content.return_value = mock_response

    mock_vision = MagicMock()
    mock_vision.return_value = {"mime_type": "image/jpeg", "data": "base64data"}

    agent = ProactiveAgent(
        session=mock_session,
        project_manager=mock_pm,
        vision_provider=mock_vision,
        genai_client=mock_client
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

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock()

    # Mock Response (Same Project)
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "app": "vscode",
        "project": "ProjectA",
        "file": "main.py",
        "repo": "owner/repo"
    })
    mock_client.aio.models.generate_content.return_value = mock_response

    mock_vision = MagicMock()
    mock_vision.return_value = {"mime_type": "image/jpeg", "data": "base64data"}

    agent = ProactiveAgent(
        session=mock_session,
        project_manager=mock_pm,
        vision_provider=mock_vision,
        genai_client=mock_client
    )

    # Run Check
    suggestion = await agent._check_context_switch()

    # Verify No Suggestion
    assert suggestion is None
