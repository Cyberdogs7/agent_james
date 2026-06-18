import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class OpenHandsAgent:
    def __init__(self, session=None, api_url=None):
        self.base_url = api_url or os.getenv("OPENHANDS_API_URL", "http://localhost:3000/api")
        self.client = httpx.AsyncClient()
        self.session_id = None
        self.session = session

        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    async def _request(self, method, url, tool_name="<unknown>", **kwargs):
        """Helper method to make requests with retry logic."""
        self._log(f"[OPENHANDS_AGENT] Requesting: {tool_name} ({method} {url})")
        if self.include_raw and "json" in kwargs:
            print(f"[OPENHANDS_AGENT] Request Body: {kwargs['json']}")
        max_retries = 3
        base_delay = 1
        for attempt in range(max_retries):
            try:
                response = await self.client.request(method, url, **kwargs)
                response_text = response.text
                self._log(f"[OPENHANDS_AGENT] Response for {tool_name}:")
                self._log(f"  - Status Code: {response.status_code}")
                self._log(f"  - Raw Data: {response_text}")

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    delay = base_delay * (2 ** attempt)
                    print(f"Rate limited (429) for OpenHands API at {url}. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    print(f"HTTP error occurred: {e}")
                    return None
            except Exception as e:
                print(f"An error occurred during request for {tool_name}: {repr(e)}")
                return None
        print(f"[OPENHANDS_AGENT] Request failed for {tool_name} after {max_retries} retries.")
        return None

    async def create_session(self, prompt, repo_path=None):
        """Creates a new session/conversation in the OpenHands API."""
        data = {
            "initial_user_msg": prompt,
        }
        if repo_path:
            # Depending on how the local openhands container is mounted, this could be the host path
            # Or if it's integrated, maybe openhands can read standard git provider config
            data["repository"] = repo_path

        session = await self._request("POST", f"{self.base_url}/conversations", tool_name="create_session", json=data)
        if session and "conversation_id" in session:
            self.session_id = session["conversation_id"]
            return session
        return None

    async def spawn_agent(self, prompt, repo_path=None, role=None, callback=None):
        """High-level method to start a conversation."""
        session = await self.create_session(prompt, repo_path)
        if session:
            # We don't have websocket polling natively integrated here yet,
            # but we can return the session object
            return session
        return None
