import asyncio
import os
import httpx
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
        self.monitored_sessions = {}
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"

        # Caching
        self._cache = {}
        self._cache_expiry = {}
        self._cache_ttl = 15 # Seconds

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

    def invalidate_cache(self, key=None):
        if key:
            self._cache.pop(key, None)
            self._cache_expiry.pop(key, None)
        else:
            self._cache.clear()
            self._cache_expiry.clear()

    async def create_session(self, prompt, source):
        """Creates a new session in the Jules API."""
        source_context = {}
        if source:
            if source.startswith("sources/"):
                source_context["source"] = source
                source_context["githubRepoContext"] = {"startingBranch": "master"}
            elif source.startswith("github/"):
                source_context["source"] = f"sources/{source}"
                source_context["githubRepoContext"] = {"startingBranch": "master"}
            else:
                # If it doesn't look like a resource name, assume it's a repo reference
                source_context["githubRepoContext"] = {
                    "repo": source,
                    "startingBranch": "master"
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

            # Invalidate session list cache so the new session appears immediately
            self.invalidate_cache("list_sessions")

        return session

    async def send_message(self, session_id, message):
        """Sends a message to a session."""
        return await self._request("POST", f"{self.base_url}/{session_id}:sendMessage", tool_name="send_message", json={"prompt": message})

    async def list_sessions(self, limit=100):
        """Lists all sessions, returning full session objects."""
        # Check Cache
        cache_key = "list_sessions"
        now = time.time()
        if cache_key in self._cache and cache_key in self._cache_expiry:
            if now < self._cache_expiry[cache_key]:
                # Valid cache
                return self._cache[cache_key]

        params = {"pageSize": limit}
        response = await self._request("GET", f"{self.base_url}/sessions", tool_name="list_sessions", params=params)
        if response and "sessions" in response:
            sessions = response["sessions"]
            # Set Cache
            self._cache[cache_key] = sessions
            self._cache_expiry[cache_key] = now + self._cache_ttl
            return sessions
        return []

    async def list_sources(self):
        """Lists all sources."""
        return await self._request("GET", f"{self.base_url}/sources", tool_name="list_sources")

    async def list_activities(self, session_id):
        """Lists all activities for a session."""
        return await self._request("GET", f"{self.base_url}/{session_id}/activities", tool_name="list_activities")

    async def start_monitoring(self, status_change_callback):
        """Starts a background task to monitor all Jules sessions for status changes."""
        self._log("[JULES_AGENT] Starting background session monitoring...")
        while True:
            try:
                # Force a fresh fetch or rely on cache?
                # Monitoring should probably be fresh or close to it.
                # If we use cached list_sessions, we might miss updates by 15s.
                # However, monitoring loop runs every 15s anyway.
                # So we can just call list_sessions and let it handle caching.

                # To ensure we catch updates, we might want to bypass cache or shorten TTL for monitoring?
                # But since list_sessions is the only way to get status, caching it effectively limits monitoring frequency too.
                # The user accepted 15s cache.

                sessions = await self.list_sessions()
                if sessions:
                    for session in sessions:
                        session_id = session.get("name")
                        current_state = session.get("state")
                        title = session.get("title", "Untitled Jules Task")

                        # Ignore completed or failed sessions
                        if current_state in ["COMPLETED", "FAILED"]:
                            if session_id in self.monitored_sessions:
                                self._log(f"[JULES_AGENT] Session {session_id} has completed or failed. Removing from monitoring.")
                                del self.monitored_sessions[session_id]
                            continue

                        previous_state = self.monitored_sessions.get(session_id)

                        if previous_state is None:
                            # New session detected, start monitoring
                            self._log(f"[JULES_AGENT] New active session found: {session_id} ('{title}'). State: {current_state}. Starting to monitor.")
                            self.monitored_sessions[session_id] = current_state
                        elif previous_state != current_state:
                            # State change detected
                            self._log(f"[JULES_AGENT] Status change for session {session_id} ('{title}'): {previous_state} -> {current_state}")
                            self.monitored_sessions[session_id] = current_state
                            if status_change_callback:
                                # Non-blocking call to the callback
                                asyncio.create_task(status_change_callback(title, current_state))

                                # Invalidate cache on state change to ensure UI gets it?
                                # If we detected it, it means our data is fresh enough or we just fetched it.
                                # Actually, if we got it from list_sessions, the cache is already updated with this state.

            except Exception as e:
                self._log(f"[JULES_AGENT] [ERR] Error in monitoring loop: {e}")

            await asyncio.sleep(15) # Poll every 15 seconds

    async def poll_for_updates(self, session_id, stop_event):
        """Polls for updates on a session until a stop event is set."""
        last_activity_count = 0
        last_activity_time = datetime.now()
        self._log(f"[JULES_AGENT] Starting to poll for updates on session: {session_id}")
        while not stop_event.is_set():
            try:
                # list_activities is not cached yet.
                # This runs for specific sessions.
                # We should NOT cache this heavily if we want near-realtime chat.
                activities_response = await self.list_activities(session_id)
                if activities_response and "activities" in activities_response:
                    activities = activities_response["activities"]
                    new_activities = activities[last_activity_count:]

                    if new_activities:
                        last_activity_time = datetime.now()  # Reset timer on new activity
                        messages_to_send = []
                        session_completed = False

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
                                session_completed = True

                            if message:
                                messages_to_send.append(message)

                        if messages_to_send and self.session:
                            try:
                                combined_message = "\n".join(messages_to_send)
                                final_message = f"Jules session update:\n{combined_message}"
                                # Add a timeout to the send operation
                                await asyncio.wait_for(
                                    self.session.send(input=final_message, end_of_turn=False),
                                    timeout=10.0
                                )
                            except asyncio.TimeoutError:
                                self._log(f"[JULES_AGENT] [ERR] Timeout sending message to session {session_id}.")
                            except Exception as e:
                                self._log(f"[JULES_AGENT] [ERR] Failed to send message for session {session_id}: {e}")

                        if session_completed:
                            self._log(f"[JULES_AGENT] Session {session_id} complete. Stopping polling.")
                            stop_event.set()

                        last_activity_count = len(activities)
                    else:
                        # No new activity, check for timeout
                        if datetime.now() - last_activity_time > timedelta(minutes=20):
                            self._log(f"[JULES_AGENT] Session {session_id} timed out due to inactivity after 20 minutes. Stopping polling.")
                            stop_event.set()

                if not stop_event.is_set():
                    await asyncio.sleep(10) # Poll more frequently

            except Exception as e:
                self._log(f"[JULES_AGENT] [ERR] Error during polling for {session_id}: {e}")
                await asyncio.sleep(60) # Wait longer on error

        self._log(f"[JULES_AGENT] Polling stopped for session: {session_id}")
