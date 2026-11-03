import asyncio
import os
import time
import json
from datetime import datetime

class ProactiveAgent:
    def __init__(self, session, project_manager, suggestion_interval=300, vision_provider=None, genai_client=None, llm_client=None):
        self.session = session
        self.project_manager = project_manager
        self.suggestion_interval = suggestion_interval  # Time in seconds
        self.vision_provider = vision_provider
        self.genai_client = genai_client
        self.llm_client = llm_client
        if self.llm_client is None:
            try:
                from backend.llm_client import get_llm_client
                self.llm_client = get_llm_client(prefer_openrouter=True)
            except Exception:
                self.llm_client = None
        self.last_suggestion_time = 0
        self.last_vision_check_time = 0

        self.last_analyzed_project = None
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    def _should_suggest(self):
        """Checks if the agent should make a suggestion based on the suggestion interval."""
        current_time = time.time()
        if current_time - self.last_suggestion_time > self.suggestion_interval:
            return True
        return False

    async def _make_suggestion(self, suggestion):
        """Sends a suggestion to the user through the AgentJames session."""
        if self.session:
            try:
                self._log(f"[PROACTIVE_AGENT] Making suggestion: {suggestion}")
                await self.session.send(
                    input=f"System Notification: {suggestion}",
                    end_of_turn=True
                )
                self.last_suggestion_time = time.time()
            except Exception as e:
                self._log(f"[PROACTIVE_AGENT] [ERR] Failed to make suggestion: {e}")

    async def _analyze_screen(self):
        """Analyzes the screen content using Vision (OpenAI-compatible vision if available)."""
        if not self.vision_provider:
            return None

        try:
            image_payload = self.vision_provider()
            if not image_payload:
                return None

            prompt = "Analyze this image. Identify the active application. If it is a code editor, identify the project name or file name. If it is a browser, identify the website or repository. Return a JSON object with keys: 'app', 'project', 'file', 'repo'."

            # Preferred: OpenAI-compatible vision via LLMClient
            if self.llm_client is not None:
                data = image_payload.get("data", b"")
                import base64
                if isinstance(data, (bytes, bytearray)):
                    b64 = base64.b64encode(bytes(data)).decode("utf-8")
                else:
                    b64 = str(data)
                mime = image_payload.get("mime_type", "image/png")
                try:
                    res = await self.llm_client.chat_completion(
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                            ],
                        }],
                        temperature=0.2,
                    )
                    text = (res.choices[0].message.content or "").strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    return json.loads(text.strip())
                except Exception as e:
                    self._log(f"[PROACTIVE_AGENT] [ERR] LLM vision analysis failed: {e}")
                    return None

            # Legacy Gemini path removed (google-genai deprecated). No vision client configured.
            self._log("[PROACTIVE_AGENT] Vision unavailable (no LLM vision client).")
            return None
        except Exception as e:
            self._log(f"[PROACTIVE_AGENT] [ERR] Vision analysis failed: {e}")
            return None

    async def _check_context_switch(self):
        """Checks for context switches using Vision."""
        analysis = await self._analyze_screen()
        if not analysis:
            return None

        detected_project = analysis.get("project")
        if detected_project:
            # Clean up detected name (simple heuristic)
            detected_project = str(detected_project).strip()

            current = self.project_manager.current_project

            # Avoid self-triggering if we just switched or if it matches
            if detected_project.lower() != current.lower() and detected_project != self.last_analyzed_project:
                self.last_analyzed_project = detected_project
                return f"I noticed you are working on '{detected_project}'. Should I switch the project context to match and run git status?"

        return None

    async def _get_contextual_suggestion(self):
        """Analyzes the project context and returns a suggestion."""
        project_path = self.project_manager.get_current_project_path()
        files = list(project_path.glob("**/*"))

        if not files:
            return "This project is empty. Would you like to create a new file?"

        # Get the last modified time of all files
        last_modified_time = max(os.path.getmtime(f) for f in files)
        time_since_last_modification = time.time() - last_modified_time

        if time_since_last_modification > 3600:  # 1 hour
            return "It's been a while since you've worked on this project. Would you like a summary of the files?"

        return None

    async def run(self):
        """The main loop for the ProactiveAgent."""
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds

            # 1. Vision Check (Context Anticipation) - Every 60s
            current_time = time.time()
            if current_time - self.last_vision_check_time > 60:
                self.last_vision_check_time = current_time
                try:
                    vision_suggestion = await self._check_context_switch()
                    if vision_suggestion:
                        await self._make_suggestion(vision_suggestion)
                        # Don't skip other checks, but update last time
                except Exception as e:
                    self._log(f"[PROACTIVE_AGENT] [ERR] Context check failed: {e}")

            if self._should_suggest():
                suggestion = await self._get_contextual_suggestion()
                if suggestion:
                    await self._make_suggestion(suggestion)
                    continue

                if not self.project_manager.get_recent_chat_history():
                    await self._make_suggestion("It looks like we haven't talked yet. Try saying 'hello' to start our conversation.")
                    continue

                now = datetime.now()
                current_date = now.date()
                greeting_type = None

                if 6 <= now.hour < 12:
                    greeting_type = "morning"
                    suggestion_text = "Good morning! Is there anything I can help you with today?"
                elif 12 <= now.hour < 18:
                    greeting_type = "afternoon"
                    suggestion_text = "Good afternoon! Is there a task I can help you with?"
                else:
                    greeting_type = "evening"
                    suggestion_text = "Good evening! Can I help you wrap up your day?"

                # Suppression mechanism: only send if we haven't sent this specific greeting today
                if getattr(self, 'last_greeting_date', None) != current_date or getattr(self, 'last_greeting_type', None) != greeting_type:
                    self.last_greeting_date = current_date
                    self.last_greeting_type = greeting_type
                    await self._make_suggestion(suggestion_text)
                else:
                    # If we already greeted them, we don't want to just keep trying immediately
                    # So we update last_suggestion_time to delay the next check
                    self.last_suggestion_time = time.time()
