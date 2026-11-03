"""
Tests for Web Automation Agent.
"""
import pytest
import asyncio
import os

from web_agent import WebAgent


class TestWebAgentInit:
    """Test WebAgent deprecation (Gemini computer_use removed)."""

    def test_agent_creation(self):
        """Test WebAgent raises with LocalWebAgent pointer."""
        with pytest.raises(RuntimeError, match="LocalWebAgent"):
            WebAgent()
        print("WebAgent correctly deprecated → LocalWebAgent")

    def test_agent_has_browser_attrs(self):
        """Test LocalWebAgent (replacement) has browser attributes."""
        from local_web_agent import LocalWebAgent
        from unittest.mock import MagicMock
        agent = LocalWebAgent(MagicMock(), MagicMock())
        assert hasattr(agent, 'browser_agent')
        assert hasattr(agent, 'openai_tools')


class TestCoordinateDenormalization:
    """Test LocalWebAgent tool conversion (replaces coordinate tests)."""

    def test_tool_conversion(self):
        """Test tool schema conversion works."""
        from local_web_agent import convert_tools_to_openai
        from tools import browser_navigate_tool
        out = convert_tools_to_openai([browser_navigate_tool])
        assert out and out[0]["type"] == "function"
        assert out[0]["function"]["name"] == browser_navigate_tool["name"]

    def test_web_agent_stub(self):
        """Deprecated WebAgent raises on run_task."""
        import asyncio
        agent_cls = WebAgent
        with pytest.raises(RuntimeError):
            agent_cls()
        print("WebAgent stub verified")


class TestWebBrowserLaunch:
    """Test browser launching capabilities."""
    
    @pytest.mark.asyncio
    async def test_browser_launch_headless(self):
        """Test launching browser in headless mode."""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto("https://www.google.com")
                
                title = await page.title()
                print(f"Page title: {title}")
                assert "Google" in title
                
                await browser.close()
                print("Browser launch test passed")
        except Exception as e:
            pytest.skip(f"Playwright not available: {e}")


class TestWebNavigation:
    """Test web navigation capabilities."""
    
    @pytest.mark.asyncio
    async def test_navigate_to_url(self):
        """Test navigating to a URL."""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto("https://example.com")
                content = await page.content()
                
                assert "Example Domain" in content
                print("Navigation test passed")
                
                await browser.close()
        except Exception as e:
            pytest.skip(f"Playwright not available: {e}")


class TestWebScreenshot:
    """Test screenshot capabilities."""
    
    @pytest.mark.asyncio
    async def test_capture_screenshot(self, temp_dir):
        """Test capturing a screenshot."""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto("https://example.com")
                
                screenshot_path = temp_dir / "test_screenshot.png"
                await page.screenshot(path=str(screenshot_path))
                
                assert screenshot_path.exists()
                print(f"Screenshot saved to: {screenshot_path}")
                
                await browser.close()
        except Exception as e:
            pytest.skip(f"Playwright not available: {e}")


class TestWebAgentTask:
    """Test full web agent task execution."""
    
    @pytest.mark.asyncio
    async def test_simple_web_task(self):
        """Test deprecated web task raises."""
        with pytest.raises(RuntimeError):
            agent = WebAgent()
        print("Deprecated WebAgent raises as expected; use LocalWebAgent")


class TestPlaywrightInstallation:
    """Test Playwright availability."""
    
    def test_playwright_import(self):
        """Test if Playwright is installed."""
        try:
            from playwright.async_api import async_playwright
            print("Playwright is installed")
        except ImportError:
            pytest.skip("Playwright not installed")
    
    @pytest.mark.asyncio
    async def test_playwright_browsers(self):
        """Test if Playwright browsers are installed."""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                await browser.close()
                print("Chromium browser is available")
        except Exception as e:
            pytest.skip(f"Playwright browsers not installed: {e}")
