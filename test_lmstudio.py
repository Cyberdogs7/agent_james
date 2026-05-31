import asyncio
import os
from openai import AsyncOpenAI
import traceback
from backend.local_web_agent import LocalWebAgent
from backend.browser_agent import ProgrammaticBrowserAgent
from backend.tool_registry import ToolRegistry

async def main():
    browser_agent = ProgrammaticBrowserAgent()
    tool_registry = ToolRegistry()
    
    agent = LocalWebAgent(browser_agent, tool_registry)
    
    async def dummy_update(img, log):
        print(f"Update: {log}")
        
    try:
        prompt = "Play the butterfly botanist mini game"
        await agent.run_task(prompt, dummy_update)
    except Exception as e:
        print(f"FAILED WITH: {e}")
        import traceback
        traceback.print_exc()
    await browser_agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
