import os

INCLUDE_RAW_LOGS = os.getenv("INCLUDE_RAW_LOGS", "True").lower() == "true"

restart_application_tool = {
    "name": "restart_application",
    "description": "Restarts the entire application, including the backend and frontend. Use this tool when the user asks to 'restart' or 'reboot' the system.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

class SystemAgent:
    def __init__(self, sio=None):
        self.tools = [restart_application_tool]
        self.sio = sio

    async def restart_application(self):
        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [RESTART] Emitting restart signal to frontend...")
        if self.sio:
            await self.sio.emit('initiate_restart')
            return "Restart signal sent to frontend."
        else:
            return "Cannot send restart signal: not connected to server."