import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class JulesAgent:
    def __init__(self, session=None):
        self.api_key = os.getenv("JULES_API_KEY")
        self.base_url = "https://jules.googleapis.com/v1alpha"
        self.client = httpx.AsyncClient(headers={"x-goog-api-key": self.api_key})
        self.session_id = None
        self.session = session
        self.active_sessions = set()
        self.sessions_lock = asyncio.Lock()

    async def _request(self, method, url, tool_name="<unknown>", **kwargs):
        """Helper method to make requests with retry logic."""
        print(f"[JULES_AGENT] Requesting: {tool_name} ({method} {url})")
        max_retries = 3
        base_delay = 1
        for attempt in range(max_retries):
            try:
                response = await self.client.request(method, url, **kwargs)
                response_text = response.text
                print(f"[JULES_AGENT] Response for {tool_name}:")
                print(f"  - Status Code: {response.status_code}")
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
        data = {
            "prompt": prompt,
            "sourceContext": {
                "source": source,
                "githubRepoContext": {
                    "startingBranch": "main"
                }
            },
            "automationMode": "AUTO_CREATE_PR",
            "title": "Jules Task"
        }
        session = await self._request("POST", f"{self.base_url}/sessions", tool_name="create_session", json=data)
        if session:
            self.session_id = session["name"]
            async with self.sessions_lock:
                self.active_sessions.add(self.session_id)
        return session

    async def send_message(self, session_id, message):
        """Sends a message to a session."""
        return await self._request("POST", f"{self.base_url}/{session_id}:sendMessage", tool_name="send_message", json={"prompt": message})

    async def list_sessions(self):
        """Lists all sessions."""
        return await self._request("GET", f"{self.base_url}/sessions", tool_name="list_sessions")

    async def list_sources(self):
        """Lists all sources."""
        return await self._request("GET", f"{self.base_url}/sources", tool_name="list_sources")

    async def list_activities(self, session_id):
        """Lists all activities for a session."""
        return await self._request("GET", f"{self.base_url}/{session_id}/activities", tool_name="list_activities")

    async def poll_for_updates(self, session_id):
        """Polls for updates on a session."""
        last_activity_count = 0
        while True:
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
                        return  # Exit the polling loop

                    if message and self.session:
                        await self.session.send(input=message, end_of_turn=False)

                last_activity_count = len(activities)
            await asyncio.sleep(60)

    async def start_persistent_polling(self):
        """Starts a persistent polling loop to check for active sessions."""
        while True:
            sessions_response = await self.list_sessions()
            if sessions_response and "sessions" in sessions_response:
                for session in sessions_response["sessions"]:
                    async with self.sessions_lock:
                        if session["name"] not in self.active_sessions:
                            self.active_sessions.add(session["name"])
                            asyncio.create_task(self.poll_for_updates(session["name"]))
            await asyncio.sleep(600)
