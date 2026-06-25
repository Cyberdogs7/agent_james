import os
import json
import base64
import asyncio
from openai import AsyncOpenAI
from backend.tools import (
    browser_navigate_tool, 
    browser_execute_javascript_tool, 
    browser_get_dom_tool, 
    browser_click_tool,
    browser_type_tool,
    browser_press_tool,
    browser_scroll_tool,
    browser_wait_tool
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
        
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            base_url = "https://openrouter.ai/api/v1"
            api_key = openrouter_key
            self.model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        else:
            base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
            if base_url and not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            api_key = "lm-studio"
            self.model = os.getenv("LM_STUDIO_MODEL", "local-model")
            
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        raw_tools = [
            browser_navigate_tool,
            browser_execute_javascript_tool,
            browser_get_dom_tool,
            browser_click_tool,
            browser_type_tool,
            browser_press_tool,
            browser_scroll_tool,
            browser_wait_tool
        ]
        self.openai_tools = convert_gemini_to_openai(raw_tools)
        self._is_interrupted = False

    def interrupt(self):
        self._is_interrupted = True

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

    async def search_and_extract(self, query: str, update_callback=None) -> dict:
        """
        Search for a query and extract key information from search results.
        Returns a dict with query, results (list of {url, title, snippet}), and raw_content.
        """
        self._is_interrupted = False
        await self._send_screenshot(update_callback, f"Searching: {query}")

        messages = [
            {"role": "system", "content": """You are a web research assistant. Search for the given query, visit the top results, extract key information, and compile a summary.

Steps:
1. Navigate to Google and search for the query
2. Visit the top 3-5 search results
3. Extract relevant information from each page
4. Compile findings into a structured response

Output your findings as a JSON object with:
- "query": the original search query
- "results": array of {url, title, snippet, key_facts}
- "summary": a 2-3 paragraph synthesis of findings
- "sources": array of URLs used"""},
            {"role": "user", "content": query}
        ]

        while not self._is_interrupted:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.openai_tools,
                    temperature=0.2
                )

                message = response.choices[0].message
                messages.append(message)

                if message.tool_calls:
                    for call in message.tool_calls:
                        print(f"[LocalWebAgent] Executing {call.function.name}...")
                        try:
                            args = json.loads(call.function.arguments)
                            result = await self.tool_registry.dispatch(call.function.name, args)
                        except Exception as e:
                            result = f"Error: {e}"

                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.function.name,
                            "content": str(result)
                        })
                        await asyncio.sleep(1)
                else:
                    # Parse the final response
                    try:
                        content = message.content
                        if content.startswith("```json"):
                            content = content[7:]
                        if content.startswith("```"):
                            content = content[3:]
                        if content.endswith("```"):
                            content = content[:-3]
                        return json.loads(content.strip())
                    except:
                        return {"query": query, "summary": message.content, "results": [], "sources": []}
            except Exception as e:
                print(f"[LocalWebAgent] Search error: {e}")
                return {"query": query, "summary": "", "results": [], "sources": [], "error": str(e)}

        return {"query": query, "summary": "Search interrupted", "results": [], "sources": []}

    async def deep_research(self, question: str, context: str = "", update_callback=None) -> str:
        """
        Perform deep research on a specific question by browsing multiple sources.
        Returns a comprehensive answer with citations.
        """
        self._is_interrupted = False
        await self._send_screenshot(update_callback, f"Deep researching: {question[:80]}...")

        system_prompt = """You are an expert research analyst. Your task is to thoroughly research a question by:
1. Searching for the question on the web
2. Visiting multiple authoritative sources
3. Extracting key facts and evidence
4. Synthesizing a comprehensive answer

Always cite your sources. If information is uncertain or conflicting, note this clearly.
Provide your answer in a clear, structured format with sections for key findings, evidence, and sources."""

        user_prompt = f"""Research Question: {question}

{f'Context: {context}' if context else ''}

Please provide a comprehensive research report on this topic. Include:
1. Key findings (3-5 bullet points)
2. Detailed analysis (2-3 paragraphs)
3. Evidence and citations from sources
4. Any caveats or uncertainties"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        max_turns = 15
        for turn in range(max_turns):
            if self._is_interrupted:
                return "Research interrupted."

            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.openai_tools,
                    temperature=0.2
                )

                message = response.choices[0].message
                messages.append(message)

                if message.tool_calls:
                    for call in message.tool_calls:
                        print(f"[LocalWebAgent] Turn {turn+1}: {call.function.name}")
                        await self._send_screenshot(update_callback, f"Turn {turn+1}: {call.function.name}")
                        try:
                            args = json.loads(call.function.arguments)
                            result = await self.tool_registry.dispatch(call.function.name, args)
                        except Exception as e:
                            result = f"Error: {e}"

                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.function.name,
                            "content": str(result)
                        })
                        await asyncio.sleep(1)
                else:
                    return message.content or "Research completed."
            except Exception as e:
                print(f"[LocalWebAgent] Deep research error: {e}")
                return f"Research error: {e}"

        return "Maximum research turns reached."

    async def run_task(self, prompt, update_callback=None):
        self._is_interrupted = False
        print(f"[LocalWebAgent] Starting task with prompt: {prompt}")
        await self._send_screenshot(update_callback, "Initializing Local Web Agent...")

        messages = [
            {"role": "system", "content": "You are an advanced web automation agent. First, create a high-level plan for how you will achieve the user's request, breaking it down into specific steps. Then, execute the steps using your tools. You may execute multiple tools in sequence if it makes sense (like typing and pressing enter), but ensure you wait for elements to appear before interacting with them."},
            {"role": "user", "content": prompt}
        ]
        
        while True:
            if self._is_interrupted:
                msg = "Task interrupted by user."
                print(f"[LocalWebAgent] {msg}")
                await self._send_screenshot(update_callback, msg)
                return msg

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
