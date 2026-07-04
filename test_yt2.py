import asyncio
from backend.providers.youtube_music import _capture_youtube_music_cookies

async def test():
    try:
        creds = await _capture_youtube_music_cookies({})
        print("CREDS:", creds)
        from backend.providers.youtube_music import _create_ytmusic_client
        client = _create_ytmusic_client(creds)
        print("CLIENT:", client)
    except Exception as e:
        print("ERROR:", e)

asyncio.run(test())
