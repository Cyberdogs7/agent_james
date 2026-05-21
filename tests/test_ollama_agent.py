import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.ollama_agent import OllamaAgent

def test_interactive_chat_loop():
    async def run_test():
        # Mock httpx response iterator
        mock_response = AsyncMock()
        mock_response.status_code = 200

        async def mock_aiter_bytes():
            yield b'{"response": "Hello", "done": false}'
            yield b'{"response": " World", "done": true}'

        mock_response.aiter_bytes = mock_aiter_bytes

        # Mock the stream context manager
        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__.return_value = mock_response

        agent = OllamaAgent()
        agent.client.stream = MagicMock(return_value=mock_stream_ctx)

        # 1. Spawn Agent
        session = await agent.spawn_agent("Test prompt", role="assistant")
        session_id = session["id"]

        # Let background task run to completion
        await asyncio.sleep(0.1)

        assert agent.sessions[session_id]["response"] == "Hello World"
        assert agent.sessions[session_id]["state"] == "COMPLETED"

        # 2. Send Message (interactive loop)
        # mock stream context again for the next message
        mock_response2 = AsyncMock()
        mock_response2.status_code = 200
        async def mock_aiter_bytes2():
            yield b'{"response": "I am", "done": false}'
            yield b'{"response": " good", "done": true}'
        mock_response2.aiter_bytes = mock_aiter_bytes2

        mock_stream_ctx2 = AsyncMock()
        mock_stream_ctx2.__aenter__.return_value = mock_response2
        agent.client.stream = MagicMock(return_value=mock_stream_ctx2)

        res = await agent.send_message(session_id, "How are you?")
        assert res["status"] == "message sent"

        # Check that previous turn was archived to history
        history = agent.sessions[session_id].get("history", [])
        assert len(history) == 1
        assert history[0]["prompt"] == "Test prompt"
        assert history[0]["response"] == "Hello World"

        # Let the second background task run
        await asyncio.sleep(0.1)

        assert agent.sessions[session_id]["prompt"] == "How are you?"
        assert agent.sessions[session_id]["response"] == "I am good"

        # 3. List Activities validation
        activities = await agent.list_activities(session_id)
        # Expected sequence: User1, Agent1, User2, Agent2 = 4 activities
        assert len(activities) == 4

        assert activities[0]["userMessage"]["content"] == "Test prompt"
        assert activities[1]["agentMessage"]["content"] == "Hello World"
        assert activities[2]["userMessage"]["content"] == "How are you?"
        assert activities[3]["agentMessage"]["content"] == "I am good"

    asyncio.run(run_test())
