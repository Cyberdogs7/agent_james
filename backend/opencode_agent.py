import asyncio
import os
import httpx
import time
import subprocess
import signal
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()


class OpenCodeAgent:
    def __init__(self, project_manager=None, base_url=None):
        self.base_url = base_url or os.getenv("OPENCODE_BASE_URL", "http://127.0.0.1:4096")
        self.project_manager = project_manager
        self._client = None
        self._client_loop = None
        self._server_process = None
        self._server_starting = False

        self.polling_tasks = {}
        self.monitored_sessions = {}
        self.session_insights = {}
        self.pending_permissions = {}  # {session_id: {permission_id: permission_obj}}
        self.workspace_map = {}  # {task_id: {"worktree_path": ..., "repo_path": ..., "branch": ...}}

        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"

        self._cache = {}
        self._cache_expiry = {}
        self._cache_ttl = 15

    async def _get_client(self):
        """Returns an httpx.AsyncClient bound to the current running event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if self._client is None or self._client_loop is not loop:
            if self._client is not None:
                try:
                    await self._client.aclose()
                except Exception:
                    pass
            self._client = httpx.AsyncClient(
                timeout=60.0,
                headers={"Content-Type": "application/json"}
            )
            self._client_loop = loop
            self._log("[OPENCODE_AGENT] Created new httpx client.")

        return self._client

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    async def _request(self, method, url, tool_name="<unknown>", directory=None, **kwargs):
        """Helper method to make requests with retry logic."""
        self._log(f"[OPENCODE_AGENT] Requesting: {tool_name} ({method} {url})")
        if self.include_raw and "json" in kwargs:
            print(f"[OPENCODE_AGENT] Request Body: {kwargs['json']}")

        client = await self._get_client()

        # Inject directory header if provided
        headers = kwargs.pop("headers", {}) or {}
        if directory:
            headers["x-opencode-directory"] = directory

        max_retries = 3
        base_delay = 1
        for attempt in range(max_retries):
            try:
                response = await client.request(method, url, headers=headers, **kwargs)
                self._log(f"[OPENCODE_AGENT] Response for {tool_name}:")
                self._log(f"  - Status Code: {response.status_code}")

                if self.include_raw:
                    response_text = await asyncio.to_thread(lambda: response.text)
                    print(f"  - Raw Data: {response_text[:500]}")

                response.raise_for_status()

                # 204 No Content (e.g. prompt_async)
                if response.status_code == 204:
                    return {"status": "ok"}

                return await asyncio.to_thread(response.json)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    delay = base_delay * (2 ** attempt)
                    print(f"[OPENCODE_AGENT] Rate limited at {url}. Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    print(f"[OPENCODE_AGENT] HTTP error: {e}")
                    return None
            except httpx.RequestError as e:
                delay = base_delay * (2 ** attempt)
                print(f"[OPENCODE_AGENT] Network error ({repr(e)}) at {url}. Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
            except Exception as e:
                print(f"[OPENCODE_AGENT] Unexpected error for {tool_name}: {repr(e)}")
                return None

        print(f"[OPENCODE_AGENT] Request failed for {tool_name} after {max_retries} retries.")
        return None

    def invalidate_cache(self, key=None):
        if key:
            self._cache.pop(key, None)
            self._cache_expiry.pop(key, None)
        else:
            self._cache.clear()
            self._cache_expiry.clear()

    # --- Server Lifecycle ---

    async def ensure_server_running(self):
        """Checks if the OpenCode server is reachable. If not, spawns it."""
        if self._server_starting:
            return True

        health = await self._health_check()
        if health:
            return True

        self._log("[OPENCODE_AGENT] Server not reachable. Attempting to start...")
        return await self._start_server()

    async def _health_check(self):
        """Check if the server is healthy."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/global/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def _start_server(self):
        """Spawn opencode serve as a background subprocess."""
        self._server_starting = True
        try:
            port = int(self.base_url.split(":")[-1]) if ":" in self.base_url else 4096
            hostname = self.base_url.split("//")[-1].split(":")[0] if "//" in self.base_url else "127.0.0.1"

            self._server_process = await asyncio.create_subprocess_exec(
                "opencode", "serve", "--port", str(port), "--hostname", hostname,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._log(f"[OPENCODE_AGENT] Started server process PID={self._server_process.pid}")

            # Wait for server to become healthy (up to 15 seconds)
            for i in range(15):
                await asyncio.sleep(1)
                if await self._health_check():
                    self._log("[OPENCODE_AGENT] Server is healthy.")
                    self._server_starting = False
                    return True

            print("[OPENCODE_AGENT] Server started but health check failed after 15s.")
            self._server_starting = False
            return False

        except FileNotFoundError:
            print("[OPENCODE_AGENT] ERROR: 'opencode' binary not found on PATH. Please install OpenCode.")
            self._server_starting = False
            return False
        except Exception as e:
            print(f"[OPENCODE_AGENT] Failed to start server: {e}")
            self._server_starting = False
            return False

    async def stop_server(self):
        """Gracefully stop the managed server subprocess."""
        if self._server_process and self._server_process.returncode is None:
            self._log(f"[OPENCODE_AGENT] Stopping server PID={self._server_process.pid}")
            try:
                self._server_process.terminate()
                await asyncio.wait_for(self._server_process.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                self._server_process.kill()
            except Exception as e:
                self._log(f"[OPENCODE_AGENT] Error stopping server: {e}")
            self._server_process = None

    # --- Workspace (Git Worktree) Management ---

    async def create_workspace(self, repo_path, task_id):
        """Create an isolated git worktree for a task. Returns the worktree path."""
        try:
            workspaces_dir = os.path.join(os.path.dirname(repo_path), "workspaces")
            os.makedirs(workspaces_dir, exist_ok=True)
            worktree_path = os.path.join(workspaces_dir, task_id)
            branch_name = f"opencode/{task_id}"

            proc = await asyncio.create_subprocess_exec(
                "git", "worktree", "add", worktree_path, "-b", branch_name, repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                print(f"[OPENCODE_AGENT] Git worktree creation failed: {stderr.decode()}")
                return None

            self.workspace_map[task_id] = {
                "worktree_path": worktree_path,
                "repo_path": repo_path,
                "branch": branch_name,
            }
            self._log(f"[OPENCODE_AGENT] Created workspace: {worktree_path} (branch: {branch_name})")
            return worktree_path

        except Exception as e:
            print(f"[OPENCODE_AGENT] Error creating workspace: {e}")
            return None

    async def remove_workspace(self, task_id):
        """Remove a git worktree after task completion."""
        ws = self.workspace_map.pop(task_id, None)
        if not ws:
            return

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "worktree", "remove", ws["worktree_path"], "--force",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            self._log(f"[OPENCODE_AGENT] Removed workspace: {ws['worktree_path']}")
        except Exception as e:
            self._log(f"[OPENCODE_AGENT] Error removing workspace: {e}")

    async def merge_workspace(self, task_id):
        """Merge a worktree branch back to the main repo."""
        ws = self.workspace_map.get(task_id)
        if not ws:
            return False

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", ws["repo_path"], "merge", ws["branch"], "--no-edit",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                print(f"[OPENCODE_AGENT] Merge failed: {stderr.decode()}")
                return False

            self._log(f"[OPENCODE_AGENT] Merged branch {ws['branch']} into {ws['repo_path']}")
            return True

        except Exception as e:
            print(f"[OPENCODE_AGENT] Error merging workspace: {e}")
            return False

    # --- Session Management ---

    async def create_session(self, title=None, directory=None):
        """Creates a new OpenCode session."""
        body = {}
        if title:
            body["title"] = title

        return await self._request(
            "POST", f"{self.base_url}/session",
            tool_name="create_session",
            directory=directory,
            json=body,
        )

    async def send_prompt(self, session_id, parts, model=None, directory=None, async_mode=True):
        """Send a message to a session. async_mode=True returns immediately (204)."""
        body = {"parts": parts}
        if model:
            body["model"] = model

        endpoint = "prompt_async" if async_mode else "message"
        return await self._request(
            "POST", f"{self.base_url}/session/{session_id}/{endpoint}",
            tool_name="send_prompt",
            directory=directory,
            json=body,
        )

    async def get_session(self, session_id, directory=None):
        """Fetch a single session by ID."""
        return await self._request(
            "GET", f"{self.base_url}/session/{session_id}",
            tool_name="get_session",
            directory=directory,
        )

    async def list_sessions(self, directory=None):
        """Lists all sessions."""
        cache_key = f"list_sessions_{directory}"
        now = time.time()
        if cache_key in self._cache and cache_key in self._cache_expiry:
            if now < self._cache_expiry[cache_key]:
                return self._cache[cache_key]

        result = await self._request(
            "GET", f"{self.base_url}/session",
            tool_name="list_sessions",
            directory=directory,
        )

        if result is not None:
            self._cache[cache_key] = result
            self._cache_expiry[cache_key] = now + self._cache_ttl

        return result

    async def list_messages(self, session_id, limit=50, directory=None):
        """Lists messages in a session."""
        return await self._request(
            "GET", f"{self.base_url}/session/{session_id}/message",
            tool_name="list_messages",
            directory=directory,
            params={"limit": limit},
        )

    async def abort_session(self, session_id, directory=None):
        """Abort a running session."""
        return await self._request(
            "POST", f"{self.base_url}/session/{session_id}/abort",
            tool_name="abort_session",
            directory=directory,
        )

    async def delete_session(self, session_id, directory=None):
        """Delete a session and all its data."""
        result = await self._request(
            "DELETE", f"{self.base_url}/session/{session_id}",
            tool_name="delete_session",
            directory=directory,
        )
        self.invalidate_cache()
        return result

    async def get_session_status(self, directory=None):
        """Get status for all sessions."""
        return await self._request(
            "GET", f"{self.base_url}/session/status",
            tool_name="get_session_status",
            directory=directory,
        )

    # --- Permission Management ---

    async def list_permissions(self, session_id, directory=None):
        """List pending permission requests for a session."""
        return await self._request(
            "GET", f"{self.base_url}/session/{session_id}/permissions",
            tool_name="list_permissions",
            directory=directory,
        )

    async def respond_permission(self, session_id, permission_id, response, remember=False, directory=None):
        """Respond to a permission request."""
        body = {"response": response}
        if remember:
            body["remember"] = True

        return await self._request(
            "POST", f"{self.base_url}/session/{session_id}/permissions/{permission_id}",
            tool_name="respond_permission",
            directory=directory,
            json=body,
        )

    # --- Polling ---

    def start_polling(self, session_id, callback=None, interceptor_callback=None, directory=None):
        """Starts a background task to poll a specific session for updates."""
        if session_id in self.polling_tasks:
            self._log(f"[OPENCODE_AGENT] Already polling session: {session_id}")
            return

        self._log(f"[OPENCODE_AGENT] Starting active polling for session: {session_id}")
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            self._poll_loop(session_id, stop_event, callback, interceptor_callback, directory)
        )
        self.polling_tasks[session_id] = {"task": task, "stop_event": stop_event}
        task.add_done_callback(lambda t: self.stop_polling(session_id))

    def stop_polling(self, session_id):
        """Stops the polling task for a specific session."""
        if session_id in self.polling_tasks:
            self._log(f"[OPENCODE_AGENT] Stopping polling for session: {session_id}")
            info = self.polling_tasks.pop(session_id)
            info["stop_event"].set()

    def dismiss_session(self, session_id):
        """Stops polling and cleans up session state."""
        self.stop_polling(session_id)
        return f"Session {session_id} dismissed."

    async def _poll_loop(self, session_id, stop_event, callback, interceptor_callback=None, directory=None):
        """Internal loop to poll for updates on a session."""
        last_message_count = 0
        last_activity_time = datetime.now()

        # Initialize message count to avoid replaying history
        try:
            initial_messages = await self.list_messages(session_id, directory=directory)
            if initial_messages and isinstance(initial_messages, list):
                last_message_count = len(initial_messages)
        except Exception:
            pass

        while not stop_event.is_set():
            try:
                # Check session status
                session_obj = await self.get_session(session_id, directory=directory)
                if session_obj is None:
                    self._log(f"[OPENCODE_AGENT] Session {session_id} not found. Assuming completed.")
                    if callback:
                        await callback(f"OpenCode Update ({session_id}):\nSession no longer available. Assuming completed.")
                    stop_event.set()
                    break

                # Check for new messages
                messages_response = await self.list_messages(session_id, directory=directory)
                if messages_response and isinstance(messages_response, list):
                    new_messages = messages_response[last_message_count:]

                    messages_to_send = []
                    session_completed = False
                    insight = None

                    if new_messages:
                        last_activity_time = datetime.now()

                        for msg_wrapper in new_messages:
                            msg_info = msg_wrapper.get("info", {})
                            msg_parts = msg_wrapper.get("parts", [])
                            role = msg_info.get("role", "unknown")

                            # Extract text content from parts
                            text_content = ""
                            for part in msg_parts:
                                if part.get("type") == "text":
                                    text_content += part.get("text", "")

                            if not text_content:
                                continue

                            # Check for permission requests in parts
                            for part in msg_parts:
                                if part.get("type") == "tool-invocation":
                                    tool_state = part.get("state", {})
                                    if tool_state.get("status") == "pending-permission":
                                        perm_id = tool_state.get("permissionId")
                                        if perm_id and interceptor_callback:
                                            self.pending_permissions.setdefault(session_id, {})[perm_id] = {
                                                "permissionId": perm_id,
                                                "tool": part.get("toolInvocation", {}).get("toolName", "unknown"),
                                                "args": tool_state.get("args", {}),
                                            }

                            if role == "assistant":
                                insight = text_content[:200]

                                if interceptor_callback:
                                    if asyncio.iscoroutinefunction(interceptor_callback):
                                        await interceptor_callback(session_id, text_content)
                                    else:
                                        interceptor_callback(session_id, text_content)
                                    continue
                                else:
                                    messages_to_send.append(text_content)

                            elif role == "tool":
                                # Tool result messages - skip for user-facing output
                                continue

                    # Check session status for completion
                    if not session_completed:
                        # OpenCode session statuses vary; check for common terminal states
                        session_status = session_obj.get("status", {})
                        status_type = session_status.get("type", "") if isinstance(session_status, dict) else str(session_status)

                        if status_type in ["completed", "idle", "ready"]:
                            # Session appears idle - check if it's been idle for a while
                            if datetime.now() - last_activity_time > timedelta(minutes=5):
                                if messages_to_send:
                                    messages_to_send.append("OpenCode task appears completed.")
                                insight = "Session Completed."
                                session_completed = True
                        elif status_type in ["failed", "error"]:
                            messages_to_send.append("OpenCode session failed.")
                            insight = "Session Failed."
                            session_completed = True

                    if insight:
                        self.session_insights[session_id] = insight

                    if messages_to_send:
                        combined_message = "\n".join(messages_to_send)
                        final_message = f"OpenCode Update ({session_id}):\n{combined_message}"

                        if callback:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(final_message)
                            else:
                                callback(final_message)

                    if session_completed:
                        self._log(f"[OPENCODE_AGENT] Session {session_id} complete. Stopping polling.")
                        stop_event.set()

                    last_message_count = len(messages_response)
                else:
                    # No messages or failed to fetch
                    if datetime.now() - last_activity_time > timedelta(minutes=10):
                        self._log(f"[OPENCODE_AGENT] Session {session_id} timed out. Stopping polling.")
                        stop_event.set()

                if not stop_event.is_set():
                    await asyncio.sleep(10)

            except Exception as e:
                self._log(f"[OPENCODE_AGENT] [ERR] Error polling {session_id}: {e}")
                await asyncio.sleep(30)

    # --- Formatted Methods (for tool dispatch) ---

    async def list_sessions_formatted(self, directory=None):
        """Returns a formatted list of OpenCode sessions."""
        try:
            sessions = await self.list_sessions(directory=directory)
            if sessions is not None:
                if isinstance(sessions, list) and sessions:
                    lines = []
                    for s in sessions:
                        sid = s.get("id", "unknown")
                        title = s.get("title", sid)
                        status = s.get("status", "unknown")
                        if isinstance(status, dict):
                            status = status.get("type", "unknown")
                        lines.append(f"- {title} ({sid}) [Status: {status}]")
                    return "\n".join(lines)
                elif isinstance(sessions, dict) and sessions:
                    # Might be a dict of session_id -> session
                    lines = []
                    for sid, s in sessions.items():
                        title = s.get("title", sid)
                        status = s.get("status", "unknown")
                        if isinstance(status, dict):
                            status = status.get("type", "unknown")
                        lines.append(f"- {title} ({sid}) [Status: {status}]")
                    return "\n".join(lines)
                return "No OpenCode sessions found."
            return "Failed to fetch OpenCode sessions."
        except Exception as e:
            return f"Error listing sessions: {str(e)}"

    async def list_messages_formatted(self, session_id, directory=None):
        """Returns a formatted list of messages for a session."""
        try:
            messages = await self.list_messages(session_id, directory=directory)
            if messages and isinstance(messages, list):
                if not messages:
                    return "No messages found."
                lines = []
                for msg_wrapper in messages[-10:]:
                    msg_info = msg_wrapper.get("info", {})
                    msg_parts = msg_wrapper.get("parts", [])
                    role = msg_info.get("role", "unknown")
                    text = ""
                    for part in msg_parts:
                        if part.get("type") == "text":
                            text += part.get("text", "")
                    if text:
                        prefix = "OpenCode" if role == "assistant" else "User" if role == "user" else "Tool"
                        lines.append(f"{prefix}: {text[:150]}...")
                return "\n".join(lines) if lines else "No readable messages found."
            return "Failed to list messages."
        except Exception as e:
            return f"Error listing messages: {str(e)}"
