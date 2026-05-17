import asyncio
import httpx
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

class OllamaAgent:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = os.getenv("OLLAMA_BASE_URL", base_url)
        self.client = httpx.AsyncClient(timeout=None)

        # State Storage
        self.sessions = {} # {id: session_obj}
        self.insights = {} # {id: "latest thought"}

    async def list_sessions(self):
        """Returns a list of all sessions in the format expected by the dashboard."""
        return list(self.sessions.values())

    def get_session_insight(self, session_id):
        """Returns the latest generated thought/content for the session."""
        return self.insights.get(session_id, "")

    async def list_activities(self, session_id):
        """Returns the activity log for the session in Jules API format."""
        session = self.sessions.get(session_id)
        if not session:
            return []

        activities = []

        # History (Previous turns)
        for item in session.get("history", []):
            activities.append({
                "userMessage": {"content": item["prompt"]},
                "createTime": item["createTime"]
            })
            activities.append({
                "agentMessage": {"content": item["response"]},
                "createTime": item["updateTime"]
            })

        # Current User Prompt
        activities.append({
            "userMessage": {"content": session["prompt"]},
            "createTime": session["createTime"]
        })

        # Current Agent Response (Streaming update)
        if session["response"]:
            activities.append({
                "agentMessage": {"content": session["response"]},
                "createTime": session["updateTime"]
            })

        return activities

    async def send_message(self, session_id, message):
        """Handles user feedback/messages for the session."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]

        # Save previous turn to history
        session.setdefault("history", []).append({
            "prompt": session["prompt"],
            "response": session["response"],
            "createTime": session["createTime"],
            "updateTime": session["updateTime"]
        })

        # Update for new turn
        session["prompt"] = message
        session["response"] = ""
        session["createTime"] = datetime.now().isoformat()
        session["updateTime"] = datetime.now().isoformat()
        session["state"] = "RUNNING"

        self.insights[session_id] = "Thinking..."

        # Restart generation task
        asyncio.create_task(self._run_generation(
            session_id, message, session["source"], session["role"], session["model"]
        ))

        return {"status": "message sent"}

    async def spawn_agent(self, prompt, source=None, role=None, model="llama3"):
        """Starts a new Ollama agent session in the background."""
        session_id = str(uuid.uuid4())

        # Format Title
        clean_prompt = prompt.replace("\n", " ").strip()
        if role:
            title = f"[{role.upper()}] {clean_prompt[:40]}..."
        else:
            title = f"Ollama: {clean_prompt[:50]}..."

        # Create Session Object matching Jules structure
        session_obj = {
            "name": session_id,
            "id": session_id,
            "title": title,
            "state": "RUNNING",
            "prompt": prompt,
            "response": "",
            "role": role,
            "source": source,
            "model": model,
            "createTime": datetime.now().isoformat(),
            "updateTime": datetime.now().isoformat(),
            "history": []
        }

        self.sessions[session_id] = session_obj
        self.insights[session_id] = "Initializing..."

        # Start background generation task
        asyncio.create_task(self._run_generation(session_id, prompt, source, role, model))

        return session_obj

    async def _run_generation(self, session_id, prompt, source, role, model):
        """Background task to run the LLM generation."""
        try:
            # 1. Build Context from Source (if provided)
            parts = []
            if role:
                parts.append(f"You are a {role}.")

            if source:
                context_str = await self._build_context(source)
                if context_str:
                    parts.append(f"Context:\n{context_str}")

            history = self.sessions[session_id].get("history", [])
            if history:
                history_text = "".join([f"User: {turn['prompt']}\nAssistant: {turn['response']}\n\n" for turn in history])
                parts.append(f"History:\n{history_text.strip()}")

            parts.append(f"Task:\n{prompt}")

            full_prompt = "\n\n".join(parts)

            # 2. Call Ollama API
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": True
            }

            async with self.client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    self.sessions[session_id]["state"] = "FAILED"
                    self.insights[session_id] = f"Error: Ollama returned {response.status_code}"
                    return

                full_response = ""
                async for chunk in response.aiter_bytes():
                    try:
                        chunk_data = json.loads(chunk)
                        token = chunk_data.get("response", "")
                        done = chunk_data.get("done", False)

                        full_response += token
                        self.sessions[session_id]["response"] = full_response
                        self.sessions[session_id]["updateTime"] = datetime.now().isoformat()

                        # Update "insight" to show tail of response
                        self.insights[session_id] = full_response[-200:]

                        if done:
                            self.sessions[session_id]["state"] = "COMPLETED"
                            self.insights[session_id] = "Generation Complete."
                            break

                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError:
            self.sessions[session_id]["state"] = "FAILED"
            self.insights[session_id] = "Error: Could not connect to Ollama. Is it running?"
        except Exception as e:
            self.sessions[session_id]["state"] = "FAILED"
            self.insights[session_id] = f"Error: {str(e)}"

    async def _build_context(self, source_path):
        """Reads files from the source path to build context."""
        return await asyncio.to_thread(self._build_context_sync, source_path)

    def _build_context_sync(self, source_path):
        """Synchronous helper for file I/O."""
        try:
            path = Path(source_path)
            if not path.exists():
                return f"Source path '{source_path}' not found."

            context = []

            if path.is_file():
                try:
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    context.append(f"--- File: {path.name} ---\n{content}\n")
                except Exception as e:
                    context.append(f"Error reading {path.name}: {e}")

            elif path.is_dir():
                skip_dirs = {'.git', 'node_modules', '__pycache__', 'venv', 'dist', 'build', '.idea', '.vscode'}
                skip_exts = {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.pdf', '.zip', '.tar', '.gz', '.bin', '.exe', '.dll', '.so', '.dylib', '.class', '.jar', '.war', '.ear'}

                for root, dirs, files in os.walk(path):
                    dirs[:] = [d for d in dirs if d not in skip_dirs]

                    for file in files:
                        if any(file.endswith(ext) for ext in skip_exts):
                            continue

                        file_path = Path(root) / file
                        try:
                            # Read first 10KB of each file
                            content = file_path.read_text(encoding='utf-8', errors='ignore')[:10000]
                            rel_path = file_path.relative_to(path)
                            context.append(f"--- File: {rel_path} ---\n{content}\n")
                        except Exception:
                            continue

            return "\n".join(context)

        except Exception as e:
            return f"Error building context: {e}"
