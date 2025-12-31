import os
import json
from giphy_client.apis.default_api import DefaultApi
from giphy_client.api_client import ApiClient

INCLUDE_RAW_LOGS = os.getenv("INCLUDE_RAW_LOGS", "True").lower() == "true"

search_gifs_tool = {
    "name": "search_gifs",
    "description": "Searches for GIFs.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "The search query."
            }
        },
        "required": ["query"]
    }
}

display_content_tool = {
    "name": "display_content",
    "description": "Displays content on the screen, such as images or widgets.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "content_type": {
                "type": "STRING",
                "description": "Use 'image' for URLs, 'widget' for data, or 'clear' to hide content."
            },
            "url": {
                "type": "STRING",
                "description": "The URL of an image."
            },
            "widget_type": {
                "type": "STRING",
                "description": "The kind of widget, e.g., 'weather'."
            },
            "data": {
                "type": "OBJECT",
                "description": "JSON data for the widget, usually from another tool."
            },
            "duration": {
                "type": "INTEGER",
                "description": "Optional duration in seconds. Defaults to a short period."
            }
        },
        "required": ["content_type"]
    }
}

class DisplayAgent:
    def __init__(self, on_display_content=None):
        self.tools = [search_gifs_tool, display_content_tool]
        self.on_display_content = on_display_content
        self.giphy_client = DefaultApi(ApiClient())

    async def search_gifs(self, query):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [GIF] Searching for GIFs with query: '{query}'")
        try:
            # Use Giphy's search endpoint
            response = self.giphy_client.gifs_search_get(os.getenv("GIPHY_API_KEY"), query, limit=5)
            if response.data:
                # Get the URL of the first GIF
                image_url = response.data[0].images.original.url
                return f"Found image: {image_url}"
            else:
                return "No images found."
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to search for images: {e}")
            return "Failed to search for images."

    async def display_content(self, content_type, url=None, widget_type=None, data=None, duration=None):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [DISPLAY] Displaying content: {content_type}")

        # If data is a string, assume it's JSON and parse it.
        # This handles the case where the model passes the result of one tool (get_weather)
        # as a stringified argument to another tool (display_content).
        parsed_data = data
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WARN] Could not decode JSON string for display content: {data}")
                pass # Leave it as a string if it's not valid JSON

        # More robust check for wrapped data, especially for weather widgets.
        # Handles cases where the model wraps the list in a dict like {'forecast': [...]} or {'daily': [...]}.
        if widget_type == 'weather' and isinstance(parsed_data, dict) and len(parsed_data) == 1:
            key = list(parsed_data.keys())[0]
            if isinstance(parsed_data[key], list):
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WEATHER WIDGET] Detected single-key dictionary wrapping the data with key '{key}'. Extracting the list.")
                parsed_data = parsed_data[key]

        if self.on_display_content:
            self.on_display_content({
                "content_type": content_type,
                "url": url,
                "widget_type": widget_type,
                "data": parsed_data,
                "duration": duration
            })
            return "Content displayed."
        else:
            return "No display content handler registered."