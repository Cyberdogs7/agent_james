import os
import asyncio
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient

class SlackAgent:
    def __init__(self, on_message=None):
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.app_token = os.getenv("SLACK_APP_TOKEN")
        self.channel_id = os.getenv("SLACK_CHANNEL_ID")
        self.client = AsyncWebClient(token=self.bot_token)
        self.socket_mode_client = SocketModeClient(
            app_token=self.app_token,
            web_client=self.client
        )
        self.on_message = on_message
        self.user_id = None

    async def send_message(self, text):
        if not self.bot_token or not self.channel_id:
            print("[SLACK] Missing SLACK_BOT_TOKEN or SLACK_CHANNEL_ID. Cannot send message.")
            return
        try:
            await self.client.chat_postMessage(
                channel=self.channel_id,
                text=text
            )
        except Exception as e:
            print(f"[SLACK] Error sending message: {e}")

    async def _handle_message(self, client, req):
        if req.type == "events_api":
            await client.send_socket_mode_response(req.envelope_id)
            payload = req.payload
            if payload["event"]["type"] == "app_mention":
                text = payload["event"]["text"]
                user_id_to_remove = f"<@{self.user_id}>"
                message_text = text.replace(user_id_to_remove, "").strip()
                if self.on_message:
                    asyncio.create_task(self.on_message(message_text))


    async def start(self):
        if not self.bot_token or not self.app_token:
            print("[SLACK] Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN. Slack agent disabled.")
            return

        try:
            response = await self.client.auth_test()
            self.user_id = response["user_id"]
            print(f"[SLACK] Authenticated as user: {self.user_id}")
        except Exception as e:
            print(f"[SLACK] Error authenticating with Slack: {e}")
            return

        self.socket_mode_client.socket_mode_request_listeners.append(self._handle_message)
        await self.socket_mode_client.connect()
        print("[SLACK] Socket Mode client connected.")
