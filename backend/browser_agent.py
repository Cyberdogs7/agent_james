import asyncio
import json
from playwright.async_api import async_playwright

class ProgrammaticBrowserAgent:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._init_lock = asyncio.Lock()

    async def _ensure_browser(self):
        """Lazily initialize the browser."""
        async with self._init_lock:
            if self.browser and not self.browser.is_connected():
                self.browser = None
                self.context = None
                self.page = None
            if self.page and self.page.is_closed():
                self.page = None

            if not self.playwright:
                self.playwright = await async_playwright().start()
                
            if not self.browser:
                # Run headless=False so the user can visually monitor what the agent is doing
                self.browser = await self.playwright.chromium.launch(headless=False)
                
            if not self.context or self.context not in self.browser.contexts:
                self.context = await self.browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
            if not self.page:
                self.page = await self.context.new_page()

    async def browser_navigate(self, url: str):
        """Navigates to a specific URL."""
        try:
            await self._ensure_browser()
            await self.page.goto(url, timeout=30000)
            return f"Successfully navigated to {url}"
        except Exception as e:
            return f"Failed to navigate: {e}"

    async def browser_execute_javascript(self, script: str):
        """Executes arbitrary JavaScript in the page and returns the result."""
        try:
            await self._ensure_browser()
            result = await self.page.evaluate(script)
            if result is None:
                return "Script executed successfully (returned None or undefined)."
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            return f"JavaScript execution error: {e}"

    async def browser_get_dom(self, selector: str = None):
        """Returns the outerHTML of the body or a specific element if a selector is provided."""
        try:
            await self._ensure_browser()
            if selector:
                element = await self.page.query_selector(selector)
                if element:
                    html = await element.evaluate("el => el.outerHTML")
                    return html
                else:
                    return f"Element with selector '{selector}' not found."
            else:
                html = await self.page.content()
                return html
        except Exception as e:
            return f"Failed to get DOM: {e}"

    async def browser_click(self, selector: str):
        """Clicks an element matching the selector using actual mouse controls and tracking."""
        try:
            await self._ensure_browser()
            element = await self.page.query_selector(selector)
            if not element:
                return f"Element with selector '{selector}' not found."
            
            await element.scroll_into_view_if_needed()
            
            # Track moving elements by updating position rapidly before clicking
            x, y = 0, 0
            for _ in range(5):
                box = await element.bounding_box()
                if not box:
                    return f"Element '{selector}' is not visible or has no bounding box."
                    
                x = box['x'] + box['width'] / 2
                y = box['y'] + box['height'] / 2
                
                await self.page.mouse.move(x, y)
                await asyncio.sleep(0.02) # Short delay to allow tracking
                
            await self.page.mouse.down()
            await asyncio.sleep(0.05) # Brief hold for the click
            await self.page.mouse.up()
            
            return f"Successfully clicked element: {selector} at ({x}, {y})"
        except Exception as e:
            return f"Failed to click element '{selector}': {e}"

    async def browser_type(self, selector: str, text: str):
        """Types text into an element."""
        try:
            await self._ensure_browser()
            element = await self.page.query_selector(selector)
            if not element:
                return f"Element with selector '{selector}' not found."
            await element.scroll_into_view_if_needed()
            await element.fill(text)
            return f"Successfully typed text into element: {selector}"
        except Exception as e:
            return f"Failed to type into element '{selector}': {e}"

    async def browser_press(self, key: str):
        """Presses a key on the keyboard."""
        try:
            await self._ensure_browser()
            await self.page.keyboard.press(key)
            return f"Successfully pressed key: {key}"
        except Exception as e:
            return f"Failed to press key '{key}': {e}"

    async def browser_scroll(self, amount: int):
        """Scrolls the page vertically by the specified amount (pixels)."""
        try:
            await self._ensure_browser()
            await self.page.mouse.wheel(0, amount)
            return f"Successfully scrolled page by {amount} pixels"
        except Exception as e:
            return f"Failed to scroll page: {e}"

    async def browser_wait(self, selector: str = None, time_ms: int = None):
        """Waits for an element to appear or waits for a specified time."""
        try:
            await self._ensure_browser()
            if selector:
                await self.page.wait_for_selector(selector, timeout=time_ms or 30000)
                return f"Successfully waited for element: {selector}"
            elif time_ms:
                await self.page.wait_for_timeout(time_ms)
                return f"Successfully waited for {time_ms} ms"
            else:
                return "Either selector or time_ms must be provided."
        except Exception as e:
            return f"Failed to wait: {e}"

    async def stop(self):
        """Closes the browser session."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
