import asyncio
from ytmusicapi import YTMusic

async def test():
    yt = YTMusic()
    results = yt.search("Rick Astley")
    print("Search results:", len(results))
    if results:
        vid = results[0].get('videoId')
        print("First video ID:", vid)

asyncio.run(test())
