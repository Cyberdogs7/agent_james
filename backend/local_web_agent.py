import os
import json
import base64
import asyncio
from openai import AsyncOpenAI
from backend.tools import (
    browser_navigate_tool, 
    browser_execute_javascript_tool, 
    browser_get_dom_tool, 
    browser_click_tool
)

def convert_gemini_to_openai(gemini_tools):
    openai_tools = []
    
    def lower_types(schema):
        if not isinstance(schema, dict):
            return schema
        new_schema = {}
        for k, v in schema.items():
            if k == "type" and isinstance(v, str):
                new_schema[k] = v.lower()
            elif isinstance(v, dict):
                new_schema[k] = lower_types(v)
            elif isinstance(v, list):
                new_schema[k] = [lower_types(i) for i in v]
            else:
                new_schema[k] = v
        return new_schema

    for decl in gemini_tools:
        decl = dict(decl) # shallow copy
        decl.pop("behavior", None)
        params = decl.get("parameters", {})
        openai_tools.append({
            "type": "function",
            "function": {
                "name": decl["name"],
                "description": decl.get("description", ""),
                "parameters": lower_types(params)
            }
        })
    return openai_tools

class LocalWebAgent:
    def __init__(self, browser_agent, tool_registry):
        self.browser_agent = browser_agent
        self.tool_registry = tool_registry
        
        base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
        if base_url and not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        api_key = os.getenv("OPENAI_API_KEY", "lm-studio")
        self.model = os.getenv("OPENAI_MODEL", "local-model")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        raw_tools = [
            browser_navigate_tool,
            browser_execute_javascript_tool,
            browser_get_dom_tool,
            browser_click_tool
        ]
        self.openai_tools = convert_gemini_to_openai(raw_tools)

    async def _send_screenshot(self, update_callback, log_msg=""):
        if not update_callback:
            return
        try:
            await self.browser_agent._ensure_browser()
            if self.browser_agent.page:
                screenshot_bytes = await self.browser_agent.page.screenshot(type="png")
                encoded_image = base64.b64encode(screenshot_bytes).decode('utf-8')
                await update_callback(encoded_image, log_msg)
            else:
                await update_callback(None, log_msg)
        except Exception as e:
            print(f"[LocalWebAgent] Error taking screenshot: {e}")
            await update_callback(None, f"Screenshot error: {e}")

    async def run_task(self, prompt, update_callback=None):
        print(f"[LocalWebAgent] Starting task with prompt: {prompt}")
        await self._send_screenshot(update_callback, "Initializing Local Web Agent...")
        
        messages = [
            {"role": "system", "content": "You are a web automation agent. You have tools to navigate, click, and evaluate javascript. Use them to fulfill the user's request. Provide a brief sentence of what you are doing before calling a tool. Call one tool at a time."},
            {"role": "user", "content": prompt}
        ]
        
        for i in range(20): # Max 20 turns
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.openai_tools,
                    temperature=0.2
                )
                
                message = response.choices[0].message
                messages.append(message)
                
                if message.content:
                    await self._send_screenshot(update_callback, f"Agent: {message.content[:100]}...")

                if message.tool_calls:
                    for call in message.tool_calls:
                        log_msg = f"Executing {call.function.name}..."
                        print(f"[LocalWebAgent] {log_msg}")
                        await self._send_screenshot(update_callback, log_msg)
                        
                        try:
                            args = json.loads(call.function.arguments)
                            result = await self.tool_registry.dispatch(call.function.name, args)
                        except Exception as e:
                            result = f"Error executing tool: {e}"
                            
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.function.name,
                            "content": str(result)
                        })
                        
                        await asyncio.sleep(1) # Give the browser a second to render
                        # Send updated screenshot after action
                        await self._send_screenshot(update_callback, f"Result: {str(result)[:100]}...")
                else:
                    msg = message.content or "Task completed."
                    print(f"[LocalWebAgent] Finished: {msg}")
                    await self._send_screenshot(update_callback, f"Finished: {msg}")
                    return msg
            except Exception as e:
                import traceback
                traceback.print_exc()
                error_msg = f"LLM Error: {e}"
                print(f"[LocalWebAgent] {error_msg}")
                await self._send_screenshot(update_callback, error_msg)
                return error_msg
                
        return "Max turns reached."
