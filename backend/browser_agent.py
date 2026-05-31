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
            if not self.playwright:
                self.playwright = await async_playwright().start()
                # Run headless=True for typical background use, but False can be useful for debugging.
                # Keeping it headless for programmatic access.
                self.browser = await self.playwright.chromium.launch(headless=True)
                self.context = await self.browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
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
        """Clicks an element matching the selector."""
        try:
            await self._ensure_browser()
            await self.page.click(selector, timeout=5000)
            return f"Successfully clicked element: {selector}"
        except Exception as e:
            return f"Failed to click element '{selector}': {e}"

    async def stop(self):
        """Closes the browser session."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
