# Integration Report: Replacing `WebAgent` with `browser-use`

## Overview
Currently, our `backend/web_agent.py` relies on Google Gemini's raw `computer_use` API (specifically configured for `gemini-2.5-flash`) and a manual Playwright wrapper to interact with the browser. This approach is highly experimental, heavily tied to a single model provider (Google), and has limited reliability and flexibility.

Integrating the open-source `browser-use` library provides a robust, provider-agnostic, and feature-rich alternative. `browser-use` handles the complexities of Playwright automation, DOM parsing, DOM element interactions, and vision, making it significantly more reliable than the raw `computer_use` API.

## Pros & Cons

### Pros
1. **Model Agnosticism:** `browser-use` natively supports a wide variety of LLM providers. As per the requirements, we can easily swap between models like LM Studio (via OpenAI-compatible local endpoints), Open Router, and Google Gemini.
2. **Abstracted DOM/Playwright Complexity:** Instead of calculating x/y coordinates and manually dispatching Playwright events, `browser-use` understands the DOM, extracting clickable elements and mapping them automatically. This drastically reduces the error rate of missed clicks.
3. **High Community Adoption & Active Maintenance:** With over 79k+ GitHub stars and active development, `browser-use` is continuously updated to handle complex website structures, captchas, and stealth browsing.
4. **Rich Tooling:** It supports custom tools out-of-the-box, allowing us to seamlessly integrate our own agentic actions with the web browser agent.
5. **Simpler Codebase:** Replaces hundreds of lines of brittle Playwright boilerplate in `web_agent.py` with a few lines of configuration.

### Cons
1. **Dependency Overhead:** Introducing `browser-use` adds a heavy dependency tree (including `langchain`, `pydantic`, etc.) which might inflate the size of our deployment footprint.
2. **Less Granular Control:** Because `browser-use` abstracts the Playwright interactions, we might lose some low-level control over exactly how keyboard and mouse events are dispatched if we need highly specialized automation.
3. **Frontend Feedback Changes:** Currently, our `WebAgent` captures screenshots and logs at every raw function call (like `click_at`, `type_text_at`) and streams them back via `update_callback`. `browser-use` manages its own internal loop (`agent.run()`), making it slightly more challenging to stream real-time visual progress out to the frontend without utilizing custom callbacks or reading state from its internal history.

---

## Implementation Plan

### 1. Update Dependencies
We need to add `browser-use` and the required LLM provider SDKs to our project:
```bash
uv pip install browser-use langchain-google-genai langchain-openai
uvx browser-use install
```

### 2. Refactor `backend/web_agent.py`
We will replace the manual Playwright loop with `browser_use.Agent`. We will design the class to accept configuration for different models (LM Studio, Open Router, Gemini).

```python
import os
import asyncio
import base64
from dotenv import load_dotenv

from browser_use import Agent, Browser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

load_dotenv()

class WebAgent:
    def __init__(self, provider="gemini", model_name=None):
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"
        self.browser = None
        self.provider = provider

        # Configure LLM based on provider
        if self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is not set")
            model = model_name or "gemini-2.5-flash"
            self.llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)

        elif self.provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY is not set")
            # Uses OpenAI compatible client for OpenRouter
            model = model_name or "anthropic/claude-3.5-sonnet"
            self.llm = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                model=model
            )

        elif self.provider == "lmstudio":
            # LM Studio exposes a local OpenAI-compatible server typically at port 1234
            model = model_name or "local-model"
            self.llm = ChatOpenAI(
                base_url="http://localhost:1234/v1",
                api_key="lm-studio",
                model=model
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def run_task(self, prompt, update_callback=None):
        """
        Runs the browser-use agent with the given prompt.
        To maintain UI streaming, we can utilize custom tool tracking or step callbacks if supported,
        or poll the browser state during execution.
        """
        if self.include_raw:
            print(f"[START] WebAgent started. Goal: {prompt}")

        self.browser = Browser()

        agent = Agent(
            task=prompt,
            llm=self.llm,
            browser=self.browser,
        )

        # Execute task
        history = await agent.run()

        # We can extract the final textual response or state from the history object
        final_result = history.final_result() if history else "Agent finished."

        if self.include_raw:
            print(f"[DONE] WebAgent finished: {final_result}")

        # Note: To restore the `update_callback` functionality (streaming screenshots to the frontend),
        # we will need to inject an intermediate step callback into the Agent or customize the
        # Browser Context to capture screenshots after specific actions.

        return final_result

if __name__ == "__main__":
    # Test with LM Studio
    agent = WebAgent(provider="lmstudio")
    asyncio.run(agent.run_task("Go to google.com and search for 'LM Studio'"))
```

### 3. Handling Frontend Visual Feedback (`update_callback`)
`browser-use` execution is abstracted behind `await agent.run()`. To restore our frontend's ability to see what the agent is doing in real-time, we have a few options:
1. **Agent Callbacks:** `browser-use` allows attaching LangChain callbacks or its own internal step handlers (depending on the library version) to trigger actions between reasoning steps.
2. **Custom Browser Wrapper:** We can pass a custom `Browser` instance and intercept Playwright commands to trigger the `update_callback(screenshot_b64, log_message)` when navigating or clicking.
3. **Polling (Easiest):** We can run a background asyncio task that periodically takes screenshots of the active Playwright page while `agent.run()` is executing and sends them to the frontend.
