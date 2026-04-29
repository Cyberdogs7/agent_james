import asyncio
import os
import httpx
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

class JulesAgent:
    def __init__(self, session=None, api_key=None, project_manager=None):
        self.api_key = api_key or os.getenv("JULES_API_KEY") or ""
        self.base_url = "https://jules.googleapis.com/v1alpha"
        self.client = httpx.AsyncClient(headers={"x-goog-api-key": self.api_key}, timeout=60.0)
        self.session_id = None
        self.session = session # Optional: Main Gemini Session (Legacy support, prefer callbacks)
        self.project_manager = project_manager
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
                print(f"An error occurred during request for {tool_name}: {repr(e)}")
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

    async def create_session(self, prompt, source, role=None, starting_branch=None):
        """Creates a new session in the Jules API."""
        source_context = {}
        if source:
            if source.startswith("github.com/"):
                source = source.replace("github.com/", "", 1)

            if source.startswith("sources/"):
                source_context["source"] = source
            elif source.startswith("github/"):
                source_context["source"] = f"sources/{source}"
            else:
                # If it doesn't look like a resource name, assume it's a repo reference
                source_context["source"] = f"sources/github/{source}"

            # API requires githubRepoContext for github sources
            if "sources/github/" in source_context["source"]:
                source_context["githubRepoContext"] = {}

                # Extract branch from source if present and not already provided
                if "/branches/" in source_context["source"]:
                    parts = source_context["source"].split("/branches/")
                    source_context["source"] = parts[0]
                    if not starting_branch:
                        starting_branch = parts[1]

                if not starting_branch:
                    # Attempt to fetch default branch from GitHub if we have a token
                    token = self.project_manager.get_github_token()
                    if token:
                        parts = source_context["source"].split("/")
                        if len(parts) >= 4:
                            owner, repo = parts[2], parts[3]
                            try:
                                client = GitHubClient(token)
                                details = await client.get_repo_details(owner, repo)
                                if details:
                                    starting_branch = details.get("default_branch")
                                    if starting_branch:
                                        print(f"[JulesAgent] Resolved default branch for {owner}/{repo}: {starting_branch}")
                            except Exception as e:
                                print(f"[JulesAgent] Failed to fetch repo details for branch resolution: {e}")

                    if not starting_branch:
                        # Fallback if GitHub fetch fails or no token
                        starting_branch = "master"

                source_context["githubRepoContext"]["startingBranch"] = starting_branch
        
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

    async def spawn_agent(self, prompt, source, role=None, callback=None, starting_branch=None):
        """High-level method to create a session and immediately start polling it."""
        session = await self.create_session(prompt, source, role=role, starting_branch=starting_branch)
        if session:
            session_id = session['name']
            self.start_polling(session_id, callback)
            return session
        return None

    async def spawn_agent_with_context(self, prompt, source, role=None, callback=None, starting_branch=None):
        """
        Enhances the prompt with architectural memory context (RAG) before spawning.
        """
        final_prompt = prompt
        if self.project_manager:
            try:
                memories = self.project_manager.search_architectural_memory(prompt)
                if memories:
                    memory_context = "\n".join([f"- {m}" for m in memories])
                    final_prompt = f"Context from previous architectural decisions & constraints:\n{memory_context}\n\nTask:\n{prompt}"
                    self._log(f"[JULES_AGENT] [MEMORY] Injected context into prompt. Length: {len(memory_context)}")
            except Exception as e:
                self._log(f"[JULES_AGENT] [ERR] Memory search failed: {e}")

        return await self.spawn_agent(final_prompt, source, role, callback, starting_branch)

    def start_polling(self, session_id, callback=None, interceptor_callback=None):
        """Starts a background task to poll a specific session for updates."""
        if session_id in self.polling_tasks:
            self._log(f"[JULES_AGENT] Already polling session: {session_id}")
            return

        self._log(f"[JULES_AGENT] Starting active polling for session: {session_id}")
        stop_event = asyncio.Event()
        task = asyncio.create_task(self._poll_loop(session_id, stop_event, callback, interceptor_callback))
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

    def dismiss_session(self, session_id):
        """Stops polling and dismisses the session from the project manager."""
        self.stop_polling(session_id)
        if self.project_manager:
            return f"Session stopped and dismissed: {self.project_manager.dismiss_jules_session(session_id)[1]}"
        return "Session stopped."

    async def _poll_loop(self, session_id, stop_event, callback, interceptor_callback=None):
        """Internal loop to poll for updates on a session."""
        last_activity_count = 0
        last_activity_time = datetime.now()

        while not stop_event.is_set():
            try:
                session_obj = await self.get_session(session_id)
                if session_obj is None:
                    # If we can't find the session, it's likely been deleted or finished
                    self._log(f"[JULES_AGENT] Session {session_id} no longer available. Assuming task completed.")
                    if callback:
                         await callback(f"Jules Update ({session_id}):\nSession is no longer available. Assuming task completed.")
                    stop_event.set()
                    break

                activities_response = await self.list_activities(session_id)

                if activities_response and "activities" in activities_response:
                    activities = activities_response["activities"]
                    new_activities = activities[last_activity_count:]

                    messages_to_send = []
                    session_completed = False
                    insight = None

                    if new_activities:
                        last_activity_time = datetime.now()

                        for activity in new_activities:
                            message = None
                            insight = None
                            if "agentMessage" in activity:
                                msg_content = activity["agentMessage"]["content"]
                                insight = msg_content

                                # Use interceptor if available for agent messages
                                if interceptor_callback:
                                    if asyncio.iscoroutinefunction(interceptor_callback):
                                        await interceptor_callback(session_id, msg_content)
                                    else:
                                        interceptor_callback(session_id, msg_content)
                                    # Skip the normal callback so A.D.A. triage can handle it
                                    continue
                                else:
                                    if "feedback" in msg_content.lower():
                                        message = f"Jules is asking for feedback on session {session_id}. Please respond."
                                    else:
                                        message = msg_content
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

                    # Explicitly check session state as activities might be delayed or miss completion
                    if session_obj and not session_completed:
                        state = session_obj.get("state")
                        if state == "COMPLETED":
                            messages_to_send.append("Jules has completed the session.")
                            insight = "Session Completed."
                            self.session_insights[session_id] = insight
                            session_completed = True
                        elif state in ["FAILED", "ERROR"]:
                            messages_to_send.append("Jules session failed. Task Execution Failed.")
                            insight = "Session Failed."
                            self.session_insights[session_id] = insight
                            session_completed = True
                        elif state == "IN_PROGRESS":
                            # CI/CD Re-run with no work case:
                            # If we have a PR (outputs exist) and it's been idle for a while, assume it's done.
                            has_outputs = bool(session_obj.get("outputs"))
                            if has_outputs and (datetime.now() - last_activity_time > timedelta(minutes=10)):
                                self._log(f"[JULES_AGENT] Session {session_id} is IN_PROGRESS but idle with outputs. Assuming completed.")
                                messages_to_send.append("Jules task appears completed (detected idle state with existing outputs).")
                                insight = "Session Completed (Idle)."
                                self.session_insights[session_id] = insight
                                session_completed = True

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
                    if datetime.now() - last_activity_time > timedelta(minutes=10):
                        self._log(f"[JULES_AGENT] Session {session_id} timed out. Stopping polling.")
                        stop_event.set()

                if not stop_event.is_set():
                    await asyncio.sleep(10)

            except Exception as e:
                self._log(f"[JULES_AGENT] [ERR] Error polling {session_id}: {e}")
                # If we get a 404 or persistent error, we should probably stop polling eventually
                # but for now we just wait and retry.
                # If get_session above returned None and we didn't break, we'll hit this or retry.
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
        if response is not None:
            sessions = response.get("sessions", [])
            self._cache[cache_key] = sessions
            self._cache_expiry[cache_key] = now + self._cache_ttl
            return sessions
        return None

    async def get_session(self, session_id):
        """Fetches a single session by ID."""
        return await self._request("GET", f"{self.base_url}/{session_id}", tool_name="get_session")

    async def get_diff(self, session_id, activity_id=None):
        """
        Retrieves the code diff (unified patch) for a session or a specific activity.
        Mimics the 'show_code_diff' tool from the MCP SDK.
        """
        if activity_id:
            # Fetch specific activity and look for changeSet artifact
            # Note: list_activities returns a list, we might need to filter or fetch single activity if API supports it.
            # The API supports GET /sessions/{id}/activities/{activityId} based on SDK inspection.
            response = await self._request("GET", f"{self.base_url}/{session_id}/activities/{activity_id}", tool_name="get_activity")
            if response:
                artifacts = response.get("artifacts", [])
                for artifact in artifacts:
                    if artifact.get("type") == "changeSet" or "changeSet" in artifact:
                        # SDK structure: artifact.changeSet.gitPatch.unidiffPatch
                        # Or artifact might be a wrapper with type="changeSet"
                        cs = artifact.get("changeSet")
                        if cs and "gitPatch" in cs:
                            return cs["gitPatch"].get("unidiffPatch")
            return None
        else:
            # Fetch session outcome
            session = await self.get_session(session_id)
            if not session:
                return None

            # Check outputs for changeSet
            outputs = session.get("outputs", [])
            for output in outputs:
                if "changeSet" in output:
                     cs = output["changeSet"]
                     if "gitPatch" in cs:
                         return cs["gitPatch"].get("unidiffPatch")

            # Fallback: Check if session object itself has an outcome field (SDK mapping logic)
            if "outcome" in session and session["outcome"]:
                # This might be processed data, but let's check structure
                pass

            return None

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

                # IMPORTANT: If sessions is None, it means the request failed.
                # Do NOT mark sessions as completed if we just failed to fetch the list.
                if sessions is not None:
                    # Tracking which sessions are currently seen
                    current_session_ids = {s.get("name") for s in sessions if s.get("name")}

                    # 1. Detect missing sessions (assume completed as requested)
                    for session_id in list(self.monitored_sessions.keys()):
                        if session_id not in current_session_ids:
                            self._log(f"[JULES_AGENT] Session {session_id} no longer returned by API. Assuming COMPLETED.")
                            if status_change_callback:
                                asyncio.create_task(status_change_callback(session_id, "Unknown Task", "COMPLETED"))
                            del self.monitored_sessions[session_id]

                    # 2. Process current sessions
                    for session in sessions:
                        session_id = session.get("name")
                        current_state = session.get("state")
                        title = session.get("title", "Untitled Jules Task")

                        if current_state in ["COMPLETED", "FAILED"]:
                            if session_id in self.monitored_sessions:
                                previous_state = self.monitored_sessions[session_id]
                                if previous_state != current_state:
                                    self._log(f"[JULES_AGENT] Status change for {session_id}: {previous_state} -> {current_state}")
                                    if status_change_callback:
                                        asyncio.create_task(status_change_callback(session_id, title, current_state))
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
                                asyncio.create_task(status_change_callback(session_id, title, current_state))

            except Exception as e:
                self._log(f"[JULES_AGENT] [ERR] Error in monitoring loop: {e}")

            await asyncio.sleep(15)

    async def list_sources_formatted(self):
        """Returns a formatted list of Jules sources."""
        try:
            response = await self.list_sources()
            if response and "sources" in response:
                sources = [s["name"] for s in response["sources"]]
                return "\n".join(sources) if sources else "No sources found."
            return "Failed to list Jules sources."
        except Exception as e:
            return f"Error listing sources: {str(e)}"

    async def list_sessions_formatted(self):
        """Returns a formatted list of Jules sessions."""
        try:
            sessions = await self.list_sessions()
            if sessions is not None:
                 if sessions:
                     # Format for readability
                     lines = []
                     for s in sessions:
                         name = s.get('name', 'Unknown')
                         state = s.get('state', 'Unknown')
                         title = s.get('title', name)
                         lines.append(f"- {title} ({name}) [State: {state}]")
                     return "\n".join(lines)
                 return "No Jules sessions found."
            return "Failed to fetch Jules sessions."
        except Exception as e:
            return f"Error listing sessions: {str(e)}"

    async def list_activities_formatted(self, session_id):
        """Returns a formatted list of activities for a session."""
        try:
            response = await self.list_activities(session_id)
            if response and "activities" in response:
                activities = response["activities"]
                if not activities:
                    return "No activities found."

                # Simple summary
                lines = []
                for act in activities[-10:]: # Last 10
                    if 'agentMessage' in act:
                        lines.append(f"Jules: {act['agentMessage']['content'][:100]}...")
                    elif 'userMessage' in act:
                        lines.append(f"User: {act['userMessage']['content'][:100]}...")
                    elif 'changeSet' in act:
                        lines.append(f"Code Change: {act.get('description', 'No description')}")

                return "\n".join(lines)
            return "Failed to list Jules activities."
        except Exception as e:
            return f"Error listing activities: {str(e)}"

    async def get_diff_formatted(self, session_id, activity_id=None):
        """Returns the diff for a session or activity."""
        try:
            diff = await self.get_diff(session_id, activity_id)
            if diff:
                return diff
            return "No code changes found."
        except Exception as e:
            return f"Error getting diff: {str(e)}"
