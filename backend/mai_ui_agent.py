import asyncio
import base64
import httpx
from playwright.async_api import async_playwright

run_web_agent_tool = {
    "name": "run_web_agent",
    "description": "Opens a web browser and performs a task according to the prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The detailed instructions for the web browser agent."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

class MAIUI_Agent:
    def __init__(self, model_name=None):
        self.tools = [run_web_agent_tool]
        self.client = httpx.AsyncClient(timeout=60.0)
        self.browser = None
        self.context = None
        self.page = None
        self.vllm_base_url = "http://localhost:8888/v1"
        self.include_raw = True
        self.model_name = model_name or "MAI-UI-8B"

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    def denormalize_x(self, x: int, width: int) -> int:
        return int((x / 1000) * width)

    def denormalize_y(self, y: int, height: int) -> int:
        return int((y / 1000) * height)

    async def execute_function_calls(self, function_calls):
        results = []
        for call in function_calls:
            fn_name = call['function']['name']
            args = call['function']['arguments']
            self._log(f"[ACTION] Action: {fn_name} {args}")
            result_data = {}
            try:
                if fn_name == "navigate":
                    await self.page.goto(args["url"])
                elif fn_name == "click":
                    await self.page.mouse.click(args["x"], args["y"])
                elif fn_name == "type":
                    await self.page.keyboard.type(args["text"])
                    if args.get("press_enter"):
                        await self.page.keyboard.press("Enter")
                else:
                    print(f"[WARN] Warning: Model requested unimplemented function {fn_name}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"[ERR] Error executing {fn_name}: {e}")
                result_data = {"error": str(e)}
            results.append((fn_name, result_data))
        return results

    async def get_function_responses(self, results):
        screenshot_bytes = await self.page.screenshot(type="png")
        return screenshot_bytes

    async def run_task(self, prompt, update_callback=None):
        """
        Runs the agent with the given prompt.
        update_callback: async function(screenshot_b64: str, logs: str)
        Returns the final response from the agent.
        """
        self._log(f"[START] MAI-UI WebAgent started. Goal: {prompt}")
        final_response = "Agent finished without a final summary."

        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
            await self.page.goto("https://www.google.com")

            if update_callback:
                initial_screenshot = await self.page.screenshot(type="png")
                encoded_image = base64.b64encode(initial_screenshot).decode('utf-8')
                await update_callback(encoded_image, "MAI-UI Agent Initialized")

            MAX_TURNS = 10
            for turn in range(MAX_TURNS):
                self._log(f"\n--- Turn {turn + 1} ---")
                screenshot_bytes = await self.page.screenshot(type="png")
                encoded_screenshot = base64.b64encode(screenshot_bytes).decode('utf-8')

                headers = {}
                json_data = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "user", "image": encoded_screenshot}
                    ]
                }

                try:
                    response = await self.client.post(f"{self.vllm_base_url}/chat/completions", headers=headers, json=json_data)
                    response.raise_for_status()
                    tool_calls = response.json()['choices'][0]['message']['tool_calls']
                except Exception as e:
                    self._log(f"[CRITICAL] Critical API Error: {e}")
                    if update_callback: await update_callback(None, f"Error: {e}")
                    break

                if not tool_calls:
                    self._log("[DONE] Task finished.")
                    if update_callback: await update_callback(None, "Task Finished")
                    break

                results = await self.execute_function_calls(tool_calls)
                screenshot_bytes = await self.get_function_responses(results)

                if update_callback:
                    encoded_image = base64.b64encode(screenshot_bytes).decode('utf-8')
                    actions_log = ", ".join([r[0] for r in results])
                    await update_callback(encoded_image, f"Executed: {actions_log}")

            await self.browser.close()
            self._log("[CLOSE] Browser closed.")
            return final_response
