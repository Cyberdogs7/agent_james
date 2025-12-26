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

    async def create_session(self, prompt, source):
        """Creates a new session in the Jules API."""
        try:
            response = await self.client.post(
                f"{self.base_url}/sessions",
                json={
                    "prompt": prompt,
                    "sourceContext": {
                        "source": source,
                        "githubRepoContext": {
                            "startingBranch": "main"
                        }
                    },
                    "automationMode": "AUTO_CREATE_PR",
                    "title": "Jules Task"
                },
            )
            response.raise_for_status()
            session = response.json()
            self.session_id = session["name"]
            async with self.sessions_lock:
                self.active_sessions.add(self.session_id)
            return session
        except httpx.HTTPStatusError as e:
            print(f"Error creating Jules session: {e}")
            return None

    async def send_message(self, session_id, message):
        """Sends a message to a session."""
        try:
            response = await self.client.post(
                f"{self.base_url}/{session_id}:sendMessage",
                json={"prompt": message},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error sending message to Jules session: {e}")
            return None

    async def list_sessions(self):
        """Lists all sessions."""
        try:
            response = await self.client.get(f"{self.base_url}/sessions")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error listing Jules sessions: {e}")
            return None

    async def list_activities(self, session_id):
        """Lists all activities for a session."""
        try:
            response = await self.client.get(f"{self.base_url}/{session_id}/activities")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error listing Jules activities: {e}")
            return None

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
            await asyncio.sleep(30)

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
            await asyncio.sleep(300)
