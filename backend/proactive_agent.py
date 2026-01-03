import asyncio
import os
import time
from datetime import datetime

class ProactiveAgent:
    def __init__(self, session, project_manager, suggestion_interval=300):
        self.session = session
        self.project_manager = project_manager
        self.suggestion_interval = suggestion_interval  # Time in seconds
        self.last_suggestion_time = 0
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
        """Sends a suggestion to the user through the AudioLoop session."""
        if self.session:
            try:
                self._log(f"[PROACTIVE_AGENT] Making suggestion: {suggestion}")
                await self.session.send(
                    input={
                        "tool_code": "proactive_suggestion",
                        "argument": {"suggestion": suggestion},
                    },
                    end_of_turn=True
                )
                self.last_suggestion_time = time.time()
            except Exception as e:
                self._log(f"[PROACTIVE_AGENT] [ERR] Failed to make suggestion: {e}")

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
            await asyncio.sleep(60)  # Check every minute
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
