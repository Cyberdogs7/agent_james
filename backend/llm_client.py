import os
from openai import AsyncOpenAI
from typing import Optional, List, Dict, Any
import json

class LLMClient:
    """Shared LLM client factory for OpenRouter (free tier) and LM Studio (local)."""
    
    def __init__(self, prefer_openrouter: bool = True):
        self.prefer_openrouter = prefer_openrouter
        self._client: Optional[AsyncOpenAI] = None
        self._model: Optional[str] = None
        self._provider: Optional[str] = None
        self._initialize()
    
    def _initialize(self):
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        if self.prefer_openrouter and openrouter_key:
            self._client = AsyncOpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1"
            )
            self._model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
            self._provider = "openrouter"
        else:
            base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
            if base_url and not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            self._client = AsyncOpenAI(api_key="lm-studio", base_url=base_url)
            self._model = os.getenv("LM_STUDIO_MODEL", "local-model")
            self._provider = "lm_studio"
    
    @property
    def client(self) -> AsyncOpenAI:
        return self._client
    
    @property
    def model(self) -> str:
        return self._model
    
    @property
    def provider(self) -> str:
        return self._provider
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.2,
        response_format: Optional[Dict] = None,
        max_tokens: Optional[int] = None
    ):
        """Unified chat completion interface."""
        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
        if response_format:
            kwargs["response_format"] = response_format
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        return await self._client.chat.completions.create(**kwargs)
    
    async def structured_completion(
        self,
        messages: List[Dict[str, Any]],
        schema: Dict[str, Any],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """Get structured JSON output using response_format."""
        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if content.strip().startswith("```json"):
                content = content.strip()[7:]
            if content.strip().startswith("```"):
                content = content.strip()[3:]
            if content.strip().endswith("```"):
                content = content.strip()[:-3]
            return json.loads(content.strip())


_default_client: Optional[LLMClient] = None

def get_llm_client(prefer_openrouter: bool = True) -> LLMClient:
    """Get or create the default shared LLM client."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient(prefer_openrouter=prefer_openrouter)
    return _default_client


# Model configurations for different tasks
MODEL_CONFIGS = {
    "research_planner": {
        "temperature": 0.3,
        "description": "Planning research questions and strategy"
    },
    "research_synthesizer": {
        "temperature": 0.2,
        "description": "Synthesizing findings from multiple sources"
    },
    "research_gap_analyzer": {
        "temperature": 0.2,
        "description": "Identifying gaps in research coverage"
    },
    "research_report_writer": {
        "temperature": 0.3,
        "description": "Writing final consolidated report"
    },
    "web_agent": {
        "temperature": 0.2,
        "description": "Web browser automation"
    }
}