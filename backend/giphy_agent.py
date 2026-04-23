import os
import random
import traceback
import asyncio
import httpx
from urllib.parse import quote
from giphy_client.apis.default_api import DefaultApi
from giphy_client.api_client import ApiClient

class GiphyAgent:
    def __init__(self):
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"
        self.giphy_client = DefaultApi(ApiClient())
        self.api_key = os.getenv("GIPHY_API_KEY")
        self.categories = [
            'I got that', 'Will do', 'Taken care of', 'What do you mean?',
            'happy', 'sad', 'angry', 'confused', 'surprised', 'laughing'
        ]
        self.max_cache_size = 1000
        self.cache_dir = os.path.join(os.getcwd(), 'public', 'reactions')

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        for cat in self.categories:
            cat_slug = quote(cat.lower()).replace('%', '_')
            os.makedirs(os.path.join(self.cache_dir, cat_slug), exist_ok=True)

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    async def search_gifs(self, query):
        """Tool-compatible search: returns a string description of the first result."""
        self._log(f"[GiphyAgent] Searching for GIFs with query: '{query}'")

        # Try local cache first
        cached_url = self._get_cached_gif(query)
        if cached_url:
            self._log(f"[GiphyAgent] Found cached GIF for search '{query}': {cached_url}")
            return f"Found image: {cached_url}"

        try:
            # Use Giphy's search endpoint
            response = self.giphy_client.gifs_search_get(self.api_key, query, limit=5)
            if response.data:
                # Get the URL of the first GIF
                image_url = response.data[0].images.original.url
                return f"Found image: {image_url}"
            else:
                return "No images found."
        except Exception as e:
            if self.include_raw:
                print(f"[GiphyAgent] [ERR] Failed to search for images: {e}")
            return "Failed to search for images."

    def _init_cache_size(self):
        """Calculates initial cache size synchronously."""
        total = 0
        if os.path.exists(self.cache_dir):
            for root, _, files in os.walk(self.cache_dir):
                total += len([f for f in files if f.endswith('.gif')])
        return total

    def start_precaching_task(self):
        """Starts the background task to precache GIFs. Should be called when loop is running."""
        # Initialize the cache size tracking once
        self.current_cache_size = self._init_cache_size()
        self._precache_task = asyncio.create_task(self._precache_loop())

    def _get_cached_gif(self, query):
        """Attempts to find a random cached GIF for the given query."""
        cat_slug = quote(query.lower()).replace('%', '_')
        query_dir = os.path.join(self.cache_dir, cat_slug)
        if os.path.exists(query_dir):
            files = [f for f in os.listdir(query_dir) if f.endswith('.gif')]
            if files:
                selected = random.choice(files)
                # Return the public URL path
                return f"/reactions/{cat_slug}/{selected}"
        return None

    async def _precache_loop(self):
        """Background loop to precache GIFs slowly over time."""
        self._log(f"[GiphyAgent] Started background precaching task.")

        # Give the system some time to start up before hitting API
        await asyncio.sleep(10)

        async with httpx.AsyncClient() as client:
            while True:
                try:
                    if not self.api_key:
                        self._log(f"[GiphyAgent] No API key, stopping precache.")
                        break

                    if self.current_cache_size >= self.max_cache_size:
                        # Cache full, sleep for a long time
                        await asyncio.sleep(3600)
                        continue

                    # Pick a random category to fetch for
                    cat = random.choice(self.categories)
                    cat_slug = quote(cat.lower()).replace('%', '_')
                    cat_dir = os.path.join(self.cache_dir, cat_slug)

                    # Random offset to get different images over time
                    offset = random.randint(0, 100)

                    # We run this in an executor since it's a sync call
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.giphy_client.gifs_search_get(self.api_key, cat, limit=10, offset=offset)
                    )

                    if response.data:
                        for gif in response.data:
                            # Check if we hit limit
                            if self.current_cache_size >= self.max_cache_size:
                                break

                            gif_id = gif.id
                            file_path = os.path.join(cat_dir, f"{gif_id}.gif")

                            if not os.path.exists(file_path):
                                url = gif.images.original.url
                                try:
                                    img_response = await client.get(url, timeout=10.0)
                                    if img_response.status_code == 200:
                                        # Write file in thread to avoid blocking event loop
                                        def write_file(p, c):
                                            with open(p, 'wb') as f:
                                                f.write(c)

                                        await loop.run_in_executor(
                                            None,
                                            write_file, file_path, img_response.content
                                        )
                                        self.current_cache_size += 1
                                        self._log(f"[GiphyAgent] Precached GIF {gif_id} for '{cat}'")
                                        # Sleep between downloads to be nice to the API
                                        await asyncio.sleep(5)
                                except Exception as e:
                                    self._log(f"[GiphyAgent] Failed to download {url}: {e}")

                    # Sleep before checking next category
                    await asyncio.sleep(30)

                except Exception as e:
                    self._log(f"[GiphyAgent] [ERR] Precache loop error: {e}")
                    await asyncio.sleep(60)

    async def get_random_gif(self, query, limit=25):
        """Returns a random GIF URL for internal UI use (e.g. reconnect)."""
        self._log(f"[GiphyAgent] Fetching random GIF for: '{query}'")

        # Try to get from cache first
        cached_url = self._get_cached_gif(query)
        if cached_url:
            self._log(f"[GiphyAgent] Found cached GIF for '{query}': {cached_url}")
            return cached_url

        try:
            response = self.giphy_client.gifs_search_get(self.api_key, query, limit=limit)
            if response.data:
                selected_gif = random.choice(response.data)
                return selected_gif.images.original.url
            return None
        except Exception as e:
            if self.include_raw:
                print(f"[GiphyAgent] [ERR] Failed to get random GIF: {e}")
            return None
