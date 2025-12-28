import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class JulesAgent:
    def __init__(self, session=None, api_key=None):
        self.api_key = api_key or os.getenv("JULES_API_KEY")
        self.base_url = "https://jules.googleapis.com/v1alpha"
        self.client = httpx.AsyncClient(headers={"x-goog-api-key": self.api_key})
        self.session_id = None
        self.session = session
        self.active_sessions = set()
        self.sessions_lock = asyncio.Lock()
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    async def _request(self, method, url, tool_name="<unknown>", **kwargs):
        """Helper method to make requests with retry logic."""
        self._log(f"[JULES_AGENT] Requesting: {tool_name} ({method} {url})")
        if self.include_raw and "json" in kwargs:
            print(f"[JULES_AGENT] Request Body: {kwargs['json']}")
        max_retries = 3
        base_delay = 1
        for attempt in range(max_retries):
            try:
                response = await self.client.request(method, url, **kwargs)
                response_text = response.text
                self._log(f"[JULES_AGENT] Response for {tool_name}:")
                self._log(f"  - Status Code: {response.status_code}")

                # Log simplified data for list_sessions to avoid "artifacts"
                if self.include_raw:
                    if tool_name == "list_sessions" and response.status_code == 200:
                        try:
                            data = response.json()
                            if "sessions" in data:
                                simplified = [{"name": s.get("name"), "state": s.get("state")} for s in data["sessions"][:10]]
                                print(f"  - Simplified Data (First 10): {simplified}")
                            else:
                                print(f"  - Raw Data: {response_text}")
                        except Exception:
                            print(f"  - Raw Data: {response_text}")
                    else:
                        print(f"  - Raw Data: {response_text}")

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    delay = base_delay * (2 ** attempt)
                    print(f"Rate limited (429) for Jules API at {url}. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    print(f"HTTP error occurred: {e}")
                    return None
            except Exception as e:
                print(f"An error occurred during request for {tool_name}: {e}")
                return None
        print(f"[JULES_AGENT] Request failed for {tool_name} after {max_retries} retries.")
        return None

    async def create_session(self, prompt, source):
        """Creates a new session in the Jules API."""
        source_context = {}
        if source:
            if source.startswith("sources/"):
                source_context["source"] = source
                source_context["githubRepoContext"] = {"startingBranch": "main"}
            elif source.startswith("github/"):
                source_context["source"] = f"sources/{source}"
                source_context["githubRepoContext"] = {"startingBranch": "main"}
            else:
                # If it doesn't look like a resource name, assume it's a repo reference
                source_context["githubRepoContext"] = {
                    "repo": source,
                    "startingBranch": "main"
                }
        
        # Sanitize title: remove newlines and limit length
        clean_title = prompt.replace("\n", " ").replace("\r", " ").strip()
        
        data = {
            "prompt": prompt,
            "automationMode": "AUTO_CREATE_PR",
            "title": f"Jules: {clean_title[:50]}"
        }
        if source_context:
            data["sourceContext"] = source_context
        
        session = await self._request("POST", f"{self.base_url}/sessions", tool_name="create_session", json=data)
        if session:
            self.session_id = session["name"]
            async with self.sessions_lock:
                self.active_sessions.add(self.session_id)
        return session

    async def send_message(self, session_id, message):
        """Sends a message to a session."""
        return await self._request("POST", f"{self.base_url}/{session_id}:sendMessage", tool_name="send_message", json={"prompt": message})

    async def list_sessions(self, limit=10):
        """Lists all sessions, returning only session name and state, limited to 10."""
        response = await self._request("GET", f"{self.base_url}/sessions", tool_name="list_sessions")
        if response and "sessions" in response:
            return [{"name": s.get("name"), "state": s.get("state")} for s in response["sessions"][:limit]]
        return response

    async def list_sources(self):
        """Lists all sources."""
        return await self._request("GET", f"{self.base_url}/sources", tool_name="list_sources")

    async def list_activities(self, session_id):
        """Lists all activities for a session."""
        return await self._request("GET", f"{self.base_url}/{session_id}/activities", tool_name="list_activities")

    async def poll_for_updates(self, session_id, stop_event):
        """Polls for updates on a session until a stop event is set."""
        last_activity_count = 0
        self._log(f"[JULES_AGENT] Starting to poll for updates on session: {session_id}")
        while not stop_event.is_set():
            try:
                activities_response = await self.list_activities(session_id)
                if activities_response and "activities" in activities_response:
                    activities = activities_response["activities"]
                    new_activities = activities[last_activity_count:]
                    for activity in new_activities:
                        message = None
                        if "agentMessage" in activity:
                            content = activity["agentMessage"]["content"]
                            if "feedback" in content.lower():
                                message = f"Jules is asking for feedback on session {session_id}. Please use the send message functionality to respond."
                            else:
                                message = content
                        elif "plan" in activity:
                            message = "Jules has generated a plan."
                        elif "sessionComplete" in activity:
                            message = "Jules has completed the session."
                            if message and self.session:
                                await self.session.send(input=message, end_of_turn=False)
                            self._log(f"[JULES_AGENT] Session {session_id} complete. Stopping polling.")
                            stop_event.set()  # Signal to stop
                            break  # Exit the inner for-loop

                        if message and self.session:
                            await self.session.send(input=message, end_of_turn=False)

                    last_activity_count = len(activities)

                if not stop_event.is_set():
                    await asyncio.sleep(10) # Poll more frequently

            except Exception as e:
                self._log(f"[JULES_AGENT] [ERR] Error during polling for {session_id}: {e}")
                await asyncio.sleep(60) # Wait longer on error

        self._log(f"[JULES_AGENT] Polling stopped for session: {session_id}")
