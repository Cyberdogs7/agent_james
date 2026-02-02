import asyncio
import os
import httpx
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

class JulesAgent:
    def __init__(self, session=None, api_key=None):
        self.api_key = api_key or os.getenv("JULES_API_KEY") or ""
        self.base_url = "https://jules.googleapis.com/v1alpha"
        self.client = httpx.AsyncClient(headers={"x-goog-api-key": self.api_key})
        self.session_id = None
        self.session = session # Optional: Main Gemini Session (Legacy support, prefer callbacks)
        self.sessions_lock = asyncio.Lock()

        # Centralized Swarm Management
        self.polling_tasks = {} # {session_id: {"task": asyncio.Task, "stop_event": asyncio.Event}}
        self.monitored_sessions = {} # {session_id: last_state}
        self.session_insights = {} # {session_id: "Last captured thought or message"}

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

    async def create_session(self, prompt, source, role=None):
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
        
        # Format title with Role if provided
        if role:
            title = f"[{role.upper()}] {clean_title[:40]}"
        else:
            title = f"Jules: {clean_title[:50]}"

        data = {
            "prompt": prompt,
            "automationMode": "AUTO_CREATE_PR",
            "title": title
        }
        if source_context:
            data["sourceContext"] = source_context
        
        session = await self._request("POST", f"{self.base_url}/sessions", tool_name="create_session", json=data)
        if session:
            self.session_id = session["name"]
            # Invalidate session list cache so the new session appears immediately
            self.invalidate_cache("list_sessions")

        return session

    async def spawn_agent(self, prompt, source, role=None, callback=None):
        """High-level method to create a session and immediately start polling it."""
        session = await self.create_session(prompt, source, role=role)
        if session:
            session_id = session['name']
            self.start_polling(session_id, callback)
            return session
        return None

    def start_polling(self, session_id, callback=None):
        """Starts a background task to poll a specific session for updates."""
        if session_id in self.polling_tasks:
            self._log(f"[JULES_AGENT] Already polling session: {session_id}")
            return

        self._log(f"[JULES_AGENT] Starting active polling for session: {session_id}")
        stop_event = asyncio.Event()
        task = asyncio.create_task(self._poll_loop(session_id, stop_event, callback))
        self.polling_tasks[session_id] = {"task": task, "stop_event": stop_event}

        # Cleanup callback
        task.add_done_callback(lambda t: self.stop_polling(session_id))

    def stop_polling(self, session_id):
        """Stops the polling task for a specific session."""
        if session_id in self.polling_tasks:
            self._log(f"[JULES_AGENT] Stopping polling for session: {session_id}")
            info = self.polling_tasks.pop(session_id)
            info["stop_event"].set()
            # We don't await the task here to avoid blocking, but it will exit soon.

    async def _poll_loop(self, session_id, stop_event, callback):
        """Internal loop to poll for updates on a session."""
        last_activity_count = 0
        last_activity_time = datetime.now()

        while not stop_event.is_set():
            try:
                activities_response = await self.list_activities(session_id)
                if activities_response and "activities" in activities_response:
                    activities = activities_response["activities"]
                    new_activities = activities[last_activity_count:]

                    if new_activities:
                        last_activity_time = datetime.now()
                        messages_to_send = []
                        session_completed = False

                        for activity in new_activities:
                            message = None
                            insight = None
                            if "agentMessage" in activity:
                                content = activity["agentMessage"]["content"]
                                insight = content
                                if "feedback" in content.lower():
                                    message = f"Jules is asking for feedback on session {session_id}. Please respond."
                                else:
                                    message = content
                            elif "plan" in activity:
                                message = "Jules has generated a plan."
                                insight = "Generating Plan..."
                            elif "sessionComplete" in activity:
                                message = "Jules has completed the session."
                                insight = "Session Completed."
                                session_completed = True

                            if insight:
                                self.session_insights[session_id] = insight

                            if message:
                                messages_to_send.append(message)

                        if messages_to_send:
                            combined_message = "\n".join(messages_to_send)
                            final_message = f"Jules Update ({session_id}):\n{combined_message}"

                            # Invoke callback if provided, else fall back to direct session send (Legacy)
                            if callback:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(final_message)
                                else:
                                    callback(final_message)
                            elif self.session:
                                # Legacy fallback
                                try:
                                    await asyncio.wait_for(
                                        self.session.send(input=final_message, end_of_turn=False),
                                        timeout=10.0
                                    )
                                except Exception as e:
                                    self._log(f"[JULES_AGENT] [ERR] Failed to send update: {e}")

                        if session_completed:
                            self._log(f"[JULES_AGENT] Session {session_id} complete. Stopping polling.")
                            stop_event.set()

                        last_activity_count = len(activities)
                    else:
                        # No new activity, check for timeout
                        if datetime.now() - last_activity_time > timedelta(minutes=20):
                            self._log(f"[JULES_AGENT] Session {session_id} timed out. Stopping polling.")
                            stop_event.set()

                if not stop_event.is_set():
                    await asyncio.sleep(10)

            except Exception as e:
                self._log(f"[JULES_AGENT] [ERR] Error polling {session_id}: {e}")
                await asyncio.sleep(60)

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
                return self._cache[cache_key]

        params = {"pageSize": limit}
        response = await self._request("GET", f"{self.base_url}/sessions", tool_name="list_sessions", params=params)
        if response and "sessions" in response:
            sessions = response["sessions"]
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

    def get_session_insight(self, session_id):
        """Returns the latest insight/thought for a specific session."""
        return self.session_insights.get(session_id)

    async def start_monitoring(self, status_change_callback):
        """Starts a background task to monitor all Jules sessions for status changes."""
        self._log("[JULES_AGENT] Starting background session monitoring...")
        while True:
            try:
                sessions = await self.list_sessions()
                if sessions:
                    for session in sessions:
                        session_id = session.get("name")
                        current_state = session.get("state")
                        title = session.get("title", "Untitled Jules Task")

                        if current_state in ["COMPLETED", "FAILED"]:
                            if session_id in self.monitored_sessions:
                                del self.monitored_sessions[session_id]
                            continue

                        previous_state = self.monitored_sessions.get(session_id)

                        if previous_state is None:
                            self._log(f"[JULES_AGENT] New active session found: {session_id}. State: {current_state}.")
                            self.monitored_sessions[session_id] = current_state
                        elif previous_state != current_state:
                            self._log(f"[JULES_AGENT] Status change for {session_id}: {previous_state} -> {current_state}")
                            self.monitored_sessions[session_id] = current_state
                            if status_change_callback:
                                asyncio.create_task(status_change_callback(title, current_state))

            except Exception as e:
                self._log(f"[JULES_AGENT] [ERR] Error in monitoring loop: {e}")

            await asyncio.sleep(15)
