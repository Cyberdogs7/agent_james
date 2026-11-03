"""Deprecated Gemini computer_use web agent — replaced by LocalWebAgent.

google-genai removed. Use backend.local_web_agent.LocalWebAgent (OpenAI-compatible:
OpenRouter / LM Studio) which drives backend.browser_agent.ProgrammaticBrowserAgent
via tool_registry dispatch with DOM selectors (more robust than coordinate clicks).

This stub is kept so old imports fail with a clear message instead of
`ValueError: Please set GEMINI_API_KEY`.
"""

SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900


class WebAgent:
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "WebAgent (Gemini computer_use) was removed with google-genai. "
            "Use backend.local_web_agent.LocalWebAgent instead."
        )

    async def run_task(self, prompt, update_callback=None):
        raise RuntimeError(
            "WebAgent (Gemini computer_use) was removed with google-genai. "
            "Use backend.local_web_agent.LocalWebAgent instead."
        )
