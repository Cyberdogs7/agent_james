import asyncio
import logging
from backend.music_agent import MusicAgent

class MockSocket:
    def __init__(self):
        self.emits = []

    async def emit(self, event, data):
        self.emits.append((event, data))

async def test_control_emits():
    sio = MockSocket()
    agent = MusicAgent(sio=sio)
    agent.is_playing = True  # Mock playing state
    agent.current_track = {"title": "Test"}

    await agent.control("pause")
    assert any(e[0] == "music_status" and e[1]["status"] == "paused" for e in sio.emits), "Pause should emit status"

    await agent.control("resume")
    assert any(e[0] == "music_status" and e[1]["status"] == "playing" for e in sio.emits), "Resume should emit status"

    print("Tests passed!")

if __name__ == "__main__":
    asyncio.run(test_control_emits())
