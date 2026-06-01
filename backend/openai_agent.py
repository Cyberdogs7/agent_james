import asyncio
import httpx
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

class OpenAIAgent:
    """An agent that interfaces with OpenAI-compatible APIs like LM Studio and OpenRouter."""
    def __init__(self, base_url="http://localhost:1234/v1"):
        self.base_url = os.getenv("OPENAI_BASE_URL", base_url)
        self.api_key = os.getenv("OPENAI_API_KEY", "lm-studio")
        self.client = httpx.AsyncClient(timeout=None)

        # State Storage
        self.sessions = {} # {id: session_obj}
        self.insights = {} # {id: "latest thought"}

    async def list_sessions(self):
        return list(self.sessions.values())

    def get_session_insight(self, session_id):
        return self.insights.get(session_id, "")

    async def list_activities(self, session_id):
        session = self.sessions.get(session_id)
        if not session:
            return []

        activities = []
        for item in session.get("history", []):
            activities.append({"userMessage": {"content": item["prompt"]}, "createTime": item["createTime"]})
            activities.append({"agentMessage": {"content": item["response"]}, "createTime": item["updateTime"]})

        activities.append({"userMessage": {"content": session["prompt"]}, "createTime": session["createTime"]})
        if session["response"]:
            activities.append({"agentMessage": {"content": session["response"]}, "createTime": session["updateTime"]})

        return activities

    async def send_message(self, session_id, message):
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        session.setdefault("history", []).append({
            "prompt": session["prompt"],
            "response": session["response"],
            "createTime": session["createTime"],
            "updateTime": session["updateTime"]
        })

        session["prompt"] = message
        session["response"] = ""
        session["createTime"] = datetime.now().isoformat()
        session["updateTime"] = datetime.now().isoformat()
        session["state"] = "RUNNING"
        self.insights[session_id] = "Thinking..."

        asyncio.create_task(self._run_generation(
            session_id, message, session["source"], session["role"], session["model"]
        ))
        return {"status": "message sent"}

    async def spawn_agent(self, prompt, source=None, role=None, model="local-model", **kwargs):
        session_id = str(uuid.uuid4())
        clean_prompt = prompt.replace("\n", " ").strip()
        title = f"[{role.upper()}] {clean_prompt[:40]}..." if role else f"Planner: {clean_prompt[:50]}..."

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
        asyncio.create_task(self._run_generation(session_id, prompt, source, role, model))
        return session_obj

    async def _run_generation(self, session_id, prompt, source, role, model):
        try:
            messages = []
            
            # System prompt
            system_content = ""
            if role:
                system_content += f"You are a {role}. Generate an execution plan for the task.\n"
            if source:
                context_str = await self._build_context(source)
                if context_str:
                    system_content += f"\nContext:\n{context_str}\n"
            
            if system_content:
                messages.append({"role": "system", "content": system_content.strip()})
                
            history = self.sessions[session_id].get("history", [])
            for turn in history:
                messages.append({"role": "user", "content": turn['prompt']})
                messages.append({"role": "assistant", "content": turn['response']})

            messages.append({"role": "user", "content": f"Task:\n{prompt}"})

            url = f"{self.base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": messages,
                "stream": True
            }

            async with self.client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    self.sessions[session_id]["state"] = "FAILED"
                    error_text = await response.aread()
                    self.insights[session_id] = f"Error: API returned {response.status_code} - {error_text.decode('utf-8')[:100]}"
                    return

                full_response = ""
                async for chunk in response.aiter_bytes():
                    chunk_str = chunk.decode("utf-8")
                    lines = chunk_str.split("\n")
                    for line in lines:
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                token = data["choices"][0]["delta"].get("content", "")
                                full_response += token
                                self.sessions[session_id]["response"] = full_response
                                self.sessions[session_id]["updateTime"] = datetime.now().isoformat()
                                self.insights[session_id] = full_response[-200:]
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

                self.sessions[session_id]["state"] = "COMPLETED"
                self.insights[session_id] = "Generation Complete."

        except httpx.ConnectError:
            self.sessions[session_id]["state"] = "FAILED"
            self.insights[session_id] = "Error: Could not connect to API. Is it running?"
        except Exception as e:
            self.sessions[session_id]["state"] = "FAILED"
            self.insights[session_id] = f"Error: {str(e)}"

    async def _build_context(self, source_path):
        return await asyncio.to_thread(self._build_context_sync, source_path)

    def _build_context_sync(self, source_path):
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
                skip_dirs = {'.git', 'node_modules', '__pycache__', 'venv', 'dist', 'build', '.idea'}
                skip_exts = {'.pyc', '.png', '.jpg', '.pdf', '.zip', '.exe', '.dll', '.jar'}
                for root, dirs, files in os.walk(path):
                    dirs[:] = [d for d in dirs if d not in skip_dirs]
                    for file in files:
                        if any(file.endswith(ext) for ext in skip_exts):
                            continue
                        file_path = Path(root) / file
                        try:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')[:10000]
                            rel_path = file_path.relative_to(path)
                            context.append(f"--- File: {rel_path} ---\n{content}\n")
                        except Exception:
                            continue
            return "\n".join(context)
        except Exception as e:
            return f"Error building context: {e}"
