import asyncio
from ytmusicapi import YTMusic
import sys

async def main():
    yt = YTMusic()
    # Let's search
    print("Trying to create a playlist...")
    try:
        # Note: We can't really create playlists on YTMusic without authentication (OAuth or headers).
        # We can implement an internal local playlist or tool for the agent instead.
        print("Checking ytmusicapi methods...")
        print([m for m in dir(yt) if "playlist" in m.lower()])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
