import os
import random
import traceback
from giphy_client.apis.default_api import DefaultApi
from giphy_client.api_client import ApiClient

class GiphyAgent:
    def __init__(self):
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"
        self.giphy_client = DefaultApi(ApiClient())
        self.api_key = os.getenv("GIPHY_API_KEY")

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    async def search_gifs(self, query):
        """Tool-compatible search: returns a string description of the first result."""
        self._log(f"[GiphyAgent] Searching for GIFs with query: '{query}'")
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

    async def get_random_gif(self, query, limit=25):
        """Returns a random GIF URL for internal UI use (e.g. reconnect)."""
        self._log(f"[GiphyAgent] Fetching random GIF for: '{query}'")
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
