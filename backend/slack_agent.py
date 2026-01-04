import os
import asyncio
import logging
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
try:
    from backend.message_deduplicator import MessageDeduplicator
except ImportError:
    from message_deduplicator import MessageDeduplicator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.bot_id = None
        self.deduplicator = MessageDeduplicator(max_size=1000)

    async def send_message(self, text):
        if not self.bot_token or not self.channel_id:
            logger.warning("[SLACK] Missing SLACK_BOT_TOKEN or SLACK_CHANNEL_ID. Cannot send message.")
            return
        try:
            await self.client.chat_postMessage(
                channel=self.channel_id,
                text=text
            )
            logger.info(f"[SLACK] Sent message to channel {self.channel_id}")
        except Exception as e:
            logger.error(f"[SLACK] Error sending message: {e}")

    async def _handle_message(self, client, req):
        logger.debug(f"[SLACK] Received event of type: {req.type}")
        if req.type == "events_api":
            await client.send_socket_mode_response(req.envelope_id)
            payload = req.payload
            event_id = payload.get("event_id")
            event = payload.get("event", {})
            event_type = event.get("type")
            user_id = event.get("user")
            bot_id = event.get("bot_id")

            # Deduplication
            if event_id and not self.deduplicator.check_and_add(event_id):
                logger.info(f"[SLACK] Duplicate event detected (ID: {event_id}). Ignoring.")
                return

            # Also try event timestamp if event_id is missing (rare)
            if not event_id:
                event_ts = event.get("event_ts")
                if event_ts and not self.deduplicator.check_and_add(event_ts):
                     logger.info(f"[SLACK] Duplicate event detected (TS: {event_ts}). Ignoring.")
                     return

            if user_id == self.user_id:
                logger.info(f"[SLACK] Ignoring event from self (user_id match: {user_id})")
                return

            if self.bot_id and bot_id == self.bot_id:
                logger.info(f"[SLACK] Ignoring event from self (bot_id match: {bot_id})")
                return

            logger.info(f"[SLACK] Received event payload type: {event_type}")

            if event_type == "app_mention":
                text = payload["event"]["text"]
                user_id_to_remove = f"<@{self.user_id}>"
                message_text = text.replace(user_id_to_remove, "").strip()
                if self.on_message:
                    logger.info(f"[SLACK] App mention detected. Forwarding message: '{message_text}'")
                    asyncio.create_task(self.on_message(message_text))


    async def start(self):
        logger.info("[SLACK] Starting SlackAgent...")
        if not self.bot_token or not self.app_token:
            logger.warning("[SLACK] Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN. Slack agent disabled.")
            return

        try:
            response = await self.client.auth_test()
            self.user_id = response["user_id"]
            self.bot_id = response.get("bot_id")
            logger.info(f"[SLACK] Authenticated as user: {self.user_id}, bot_id: {self.bot_id}")
        except Exception as e:
            logger.error(f"[SLACK] Error authenticating with Slack: {e}")
            return

        self.socket_mode_client.socket_mode_request_listeners.append(self._handle_message)

        try:
            await self.socket_mode_client.connect()
            logger.info("[SLACK] Socket Mode client connected and listening.")
        except Exception as e:
            logger.error(f"[SLACK] CRITICAL: Socket Mode client failed to connect: {e}")

        # Keep the task alive to listen for events
        await asyncio.Event().wait()
