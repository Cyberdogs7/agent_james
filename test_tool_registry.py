import asyncio
from backend.tool_registry import ToolRegistry

async def test():
    registry = ToolRegistry()

    async def async_handler():
        return "async success"

    registry.register("my_async_tool", async_handler)

    result = await registry.dispatch("my_async_tool", {})
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(test())
