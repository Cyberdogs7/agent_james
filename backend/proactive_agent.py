import asyncio
import os
import time
import json
from datetime import datetime
import pyperclip

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

class ProactiveAgent:
    def __init__(self, session, project_manager, suggestion_interval=300, vision_provider=None, genai_client=None):
        self.session = session
        self.project_manager = project_manager
        self.suggestion_interval = suggestion_interval  # Time in seconds
        self.vision_provider = vision_provider
        self.genai_client = genai_client
        self.last_suggestion_time = 0
        self.last_vision_check_time = 0
        self.last_clipboard_content = ""
        self.last_analyzed_project = None
        self.clipboard_failure_count = 0
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

    async def _check_clipboard(self):
        """Checks the clipboard for actionable content."""
        try:
            # Run in executor to avoid blocking loop
            content = await asyncio.to_thread(pyperclip.paste)
            content = content.strip()

            # Reset failure count on success
            self.clipboard_failure_count = 0

            if not content:
                return None

            if content == self.last_clipboard_content:
                return None

            self.last_clipboard_content = content

            # Simple Heuristics
            if content.startswith("http://") or content.startswith("https://"):
                return "I noticed you copied a link. Should I open it or summarize it?"

            # Check for code-like patterns
            if any(k in content for k in ["def ", "class ", "import ", "function ", "const ", "var ", "let "]):
                # Only if it's multi-line or long enough to be interesting
                if len(content.split('\n')) > 1 or len(content) > 40:
                    return "I noticed you copied some code. Should I explain it or create a file?"

            # Check for errors
            if "error" in content.lower() or "exception" in content.lower() or "traceback" in content.lower():
                return "I noticed an error message. Should I help debug it?"

            return None

        except Exception as e:
            self.clipboard_failure_count += 1
            if self.clipboard_failure_count <= 5:
                self._log(f"[PROACTIVE_AGENT] [WARN] Clipboard check failed: {e}")
            return None

    async def _make_suggestion(self, suggestion):
        """Sends a suggestion to the user through the AudioLoop session."""
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
        """Analyzes the screen content using Vision."""
        if not self.vision_provider or not self.genai_client:
            return None

        try:
            image_payload = self.vision_provider()
            if not image_payload:
                return None

            # Create prompt
            prompt = "Analyze this image. Identify the active application. If it is a code editor, identify the project name or file name. If it is a browser, identify the website or repository. Return a JSON object with keys: 'app', 'project', 'file', 'repo'."

            # Prepare contents
            response = await self.genai_client.aio.models.generate_content(
                model="gemini-1.5-flash",
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=prompt),
                            types.Part(inline_data=types.Blob(
                                mime_type=image_payload["mime_type"],
                                data=image_payload["data"]
                            ))
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            if response.text:
                text = response.text.strip()
                # Robust JSON extraction
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                return json.loads(text.strip())
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

            # 0. Clipboard Check (Fast)
            try:
                clipboard_suggestion = await self._check_clipboard()
                if clipboard_suggestion:
                    await self._make_suggestion(clipboard_suggestion)
            except Exception as e:
                self._log(f"[PROACTIVE_AGENT] [ERR] Clipboard check failed: {e}")

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
                if 6 <= now.hour < 12:
                    await self._make_suggestion("Good morning! Is there anything I can help you with today?")
                elif 12 <= now.hour < 18:
                    await self._make_suggestion("Good afternoon! Is there a task I can help you with?")
                else:
                    await self._make_suggestion("Good evening! Can I help you wrap up your day?")
