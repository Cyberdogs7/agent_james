import asyncio
import traceback

class ToolRegistry:
    def __init__(self):
        self._handlers = {}

    def register(self, name, handler):
        """Registers a tool handler."""
        self._handlers[name] = handler

    def get_handler(self, name):
        """Returns the handler for a tool."""
        return self._handlers.get(name)

    def is_confirmation_required(self, tool_name):
        """Checks if a tool requires user confirmation."""
        destructive_keywords = ['delete', 'remove', 'wipe', 'destroy', 'dismiss', 'stop_jules']
        return any(keyword in tool_name.lower() for keyword in destructive_keywords)

    async def dispatch(self, tool_name, args):
        """
        Dispatches the tool call to the registered handler.
        """
        if tool_name not in self._handlers:
            return f"Tool '{tool_name}' not found."

        handler = self._handlers[tool_name]

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(**args)
            else:
                return handler(**args)
        except Exception as e:
            traceback.print_exc()
            return f"Error executing '{tool_name}': {str(e)}"
