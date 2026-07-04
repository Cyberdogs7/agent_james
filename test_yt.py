import asyncio
from backend.providers.youtube_music import _capture_youtube_music_cookies

async def test():
    await _capture_youtube_music_cookies({})

asyncio.run(test())
