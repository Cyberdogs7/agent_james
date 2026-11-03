"""Raw OpenAI-compatible LLM client (httpx, no openai SDK).

Mirrors the pattern used in the anime project
(`studio/clients/lmstudio.py`, `tools/fetch_library.py`):
- direct ``POST {base_url}/chat/completions`` via httpx (sync + async)
- ``response_format`` is NEVER sent — local servers (LM Studio) 400 on it.
  JSON structure is enforced by prompt instruction + robust ``_extract_json``
- ``max_tokens``/``max_output_tokens`` omitted by default so reasoning models
  are not truncated (env ``JAMES_MAX_OUTPUT_TOKENS`` > 0 sets a ceiling)
- SSE streaming supported with ``data:`` parsing and ``[DONE]`` terminator
- retries with backoff; tool-call passthrough for OpenAI-style ``tools``

Provider chain: explicit ``JAMES_LLM_*`` override → OpenRouter (cloud) →
LM Studio (local) → Ollama OpenAI-compat ``/v1`` (local).
Ollama note: point ``LM_STUDIO_BASE_URL=http://localhost:11434/v1`` with
``LM_STUDIO_MODEL=llama3`` (or set ``OLLAMA_BASE_URL``/``OLLAMA_MODEL``).
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import httpx


class RawLLMError(RuntimeError):
    pass


def _effective_output_cap(caller: int | None) -> int | None:
    """Decide the outgoing output-token cap. ``None`` = DON'T SEND IT.

    ``JAMES_MAX_OUTPUT_TOKENS``: 0 (default) -> omit the field entirely so the
    model/server decides (its own max, or until EOS). N > 0 -> ceiling of
    max(caller hint, N). A client-side cap buys nothing (billing is on actual
    tokens) and only truncates reasoning models -> empty/partial JSON.
    """
    try:
        floor = int(os.getenv("JAMES_MAX_OUTPUT_TOKENS", "0") or 0)
    except (TypeError, ValueError):
        floor = 0
    if floor <= 0:
        return None
    try:
        return max(int(caller or 0), floor)
    except (TypeError, ValueError):
        return floor


def _extract_json(text: str) -> Dict[str, Any]:
    """Best-effort JSON extraction (direct parse, code fences, balanced object)."""
    text = (text or "").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        pass
                    break
    raise RawLLMError(f"No valid JSON in model output: {text[:200]!r}")


def _to_dict_message(m: Any) -> Dict[str, Any]:
    """Normalize SDK-style message objects and plain dicts to raw dicts."""
    if isinstance(m, dict):
        return m
    content = getattr(m, "content", "")
    role = getattr(m, "role", "assistant")
    out: Dict[str, Any] = {"role": role, "content": content or ""}
    tool_calls = getattr(m, "tool_calls", None)
    if tool_calls:
        norm = []
        for tc in tool_calls:
            if isinstance(tc, dict):
                norm.append(tc)
                continue
            fn = getattr(tc, "function", None)
            norm.append({
                "id": getattr(tc, "id", ""),
                "type": getattr(tc, "type", "function"),
                "function": {
                    "name": getattr(fn, "name", "") if fn is not None else getattr(tc, "name", ""),
                    "arguments": getattr(fn, "arguments", "{}") if fn is not None else "{}",
                },
            })
        out["tool_calls"] = norm
    return out


class _Function:
    def __init__(self, name: str = "", arguments: str = "{}"):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, call_id: str = "", name: str = "", arguments: str = "{}"):
        self.id = call_id
        self.type = "function"
        self.function = _Function(name, arguments)


class _Message:
    def __init__(self, content: str = "", tool_calls: Optional[List[_ToolCall]] = None):
        self.role = "assistant"
        self.content = content or ""
        self.tool_calls = tool_calls or []

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [{
                "id": tc.id, "type": tc.type,
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            } for tc in self.tool_calls]
        return d


class _Choice:
    def __init__(self, message: _Message):
        self.message = message


class _Resp:
    """Minimal OpenAI-SDK-shaped response (`.choices[0].message.content/.tool_calls`)."""
    def __init__(self, content: str = "", tool_calls: Optional[List[_ToolCall]] = None):
        self.choices = [_Choice(_Message(content, tool_calls))]
        self._content = content

    @property
    def content(self) -> str:
        return self._content


class RawLLMClient:
    """Raw httpx client for any OpenAI-compatible ``/chat/completions`` endpoint."""

    def __init__(self, base_url: str, api_key: str = "", model: str = "",
                 timeout: float = 120.0):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or ""
        self.timeout = float(timeout or 120.0)

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        referer = os.getenv("OPENROUTER_REFERER", "")
        title = os.getenv("OPENROUTER_TITLE", "Agent James")
        if "openrouter" in self.base_url:
            if referer:
                h["HTTP-Referer"] = referer
            if title:
                h["X-Title"] = title
        return h

    def _post(self, body: Dict[str, Any]) -> Dict[str, Any]:
        timeout = httpx.Timeout(connect=min(self.timeout, 30.0), read=self.timeout,
                                write=None, pool=None)
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{self.base_url}/chat/completions",
                               json=body, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def _apost(self, body: Dict[str, Any]) -> Dict[str, Any]:
        timeout = httpx.Timeout(connect=min(self.timeout, 30.0), read=self.timeout,
                                write=None, pool=None)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self.base_url}/chat/completions",
                                     json=body, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _parse(data: Dict[str, Any]) -> tuple[str, List[_ToolCall]]:
        try:
            msg = (data.get("choices") or [{}])[0].get("message") or {}
        except Exception:
            msg = {}
        content = msg.get("content") or ""
        calls: List[_ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            calls.append(_ToolCall(
                call_id=tc.get("id", ""),
                name=fn.get("name", ""),
                arguments=fn.get("arguments", "{}"),
            ))
        return content, calls

    async def achat(self, messages: List[Any], temperature: float = 0.2,
                    max_tokens: int | None = None,
                    tools: Optional[List[Dict]] = None,
                    retries: int = 3) -> _Resp:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [_to_dict_message(m) for m in messages],
            "temperature": temperature,
        }
        cap = _effective_output_cap(max_tokens)
        if cap is not None:
            body["max_tokens"] = cap
        if tools:
            body["tools"] = tools
        last: Exception | None = None
        for attempt in range(max(1, retries)):
            try:
                data = await self._apost(body)
                content, calls = self._parse(data)
                return _Resp(content, calls)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last = exc
                time.sleep(1.5 * (attempt + 1))
        raise RawLLMError(f"chat failed after {retries} attempts: {last}")

    def chat(self, messages: List[Any], temperature: float = 0.2,
             max_tokens: int | None = None,
             tools: Optional[List[Dict]] = None,
             retries: int = 3) -> _Resp:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [_to_dict_message(m) for m in messages],
            "temperature": temperature,
        }
        cap = _effective_output_cap(max_tokens)
        if cap is not None:
            body["max_tokens"] = cap
        if tools:
            body["tools"] = tools
        last: Exception | None = None
        for attempt in range(max(1, retries)):
            try:
                data = self._post(body)
                content, calls = self._parse(data)
                return _Resp(content, calls)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last = exc
                time.sleep(1.5 * (attempt + 1))
        raise RawLLMError(f"chat failed after {retries} attempts: {last}")

    async def achat_stream(self, messages: List[Any], temperature: float = 0.2,
                           max_tokens: int | None = None,
                           tools: Optional[List[Dict]] = None,
                           on_progress=None) -> str:
        """Stream a completion; calls ``on_progress(n, partial_text)`` per delta."""
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [_to_dict_message(m) for m in messages],
            "temperature": temperature,
            "stream": True,
        }
        cap = _effective_output_cap(max_tokens)
        if cap is not None:
            body["max_tokens"] = cap
        if tools:
            body["tools"] = tools
        parts: List[str] = []
        timeout = httpx.Timeout(connect=min(self.timeout, 30.0), read=300.0,
                                write=None, pool=None)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions",
                                     json=body, headers=self._headers()) as resp:
                resp.raise_for_status()
                n = 0
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        delta = (((json.loads(payload).get("choices") or [{}])[0]
                                  .get("delta") or {}).get("content", ""))
                    except Exception:
                        continue
                    if delta:
                        parts.append(delta)
                        n += 1
                        if on_progress:
                            on_progress(n, "".join(parts))
        return "".join(parts)

    async def achat_json(self, messages: List[Any], temperature: float = 0.2,
                         max_tokens: int | None = None, retries: int = 3) -> Dict[str, Any]:
        """Prompt-enforced JSON (no ``response_format``) with fresh-generation retries."""
        last: Exception | None = None
        for attempt in range(max(1, retries)):
            try:
                resp = await self.achat(messages, temperature=temperature,
                                        max_tokens=max_tokens)
                return _extract_json(resp.choices[0].message.content)
            except (RawLLMError, Exception) as exc:
                last = exc
                if attempt < retries - 1:
                    time.sleep(1.0 * (attempt + 1))
        raise RawLLMError(f"chat_json failed after {retries} attempts: {last}")

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/models")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False


def _resolve_target(prefer_openrouter: bool = True) -> tuple[str, str, str, str]:
    """Return (base_url, api_key, model, provider)."""
    override_base = os.getenv("JAMES_LLM_BASE_URL", "")
    if override_base:
        return (override_base.rstrip("/"),
                os.getenv("JAMES_LLM_KEY", ""),
                os.getenv("JAMES_LLM_MODEL", "local-model"),
                os.getenv("JAMES_LLM_PROVIDER", "custom"))

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if prefer_openrouter and openrouter_key:
        return ("https://openrouter.ai/api/v1", openrouter_key,
                os.getenv("JAMES_MODEL", os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")),
                "openrouter")

    lm_base = os.getenv("LM_STUDIO_BASE_URL", "")
    lm_model = os.getenv("LM_STUDIO_MODEL", "")
    ollama_base = os.getenv("OLLAMA_BASE_URL", "")
    if ollama_base and not lm_base:
        base = ollama_base.rstrip("/") + ("" if ollama_base.rstrip("/").endswith("/v1") else "/v1")
        return (base, os.getenv("OLLAMA_API_KEY", ""),
                os.getenv("JAMES_MODEL", os.getenv("OLLAMA_MODEL", "llama3")),
                "ollama")
    return ((lm_base or "http://localhost:1234/v1").rstrip("/"),
            os.getenv("JAMES_LLM_KEY", "lm-studio"),
            os.getenv("JAMES_MODEL", lm_model or "local-model"),
            "lm_studio")


class LLMClient:
    """Shared raw LLM client (OpenRouter → LM Studio → Ollama /v1)."""

    def __init__(self, prefer_openrouter: bool = True):
        self.prefer_openrouter = prefer_openrouter
        self._raw: RawLLMClient | None = None
        self._model: Optional[str] = None
        self._provider: Optional[str] = None
        self._initialize()

    def _initialize(self):
        base_url, api_key, model, provider = _resolve_target(self.prefer_openrouter)
        timeout = float(os.getenv("JAMES_LLM_TIMEOUT", "120") or 120)
        self._raw = RawLLMClient(base_url=base_url, api_key=api_key,
                                 model=model, timeout=timeout)
        self._model = model
        self._provider = provider

    @property
    def client(self) -> RawLLMClient:
        assert self._raw is not None
        return self._raw

    @property
    def model(self) -> str:
        return self._model or ""

    @property
    def provider(self) -> str:
        return self._provider or ""

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.2,
        response_format: Optional[Dict] = None,
        max_tokens: Optional[int] = None,
    ):
        """Unified chat completion interface (raw httpx; ``response_format`` ignored).

        Pass ``response_format={"type": "json_object"}`` only as a hint: a
        JSON-only instruction is appended instead of sending the field, since
        local servers 400 on it.
        """
        msgs = list(messages)
        if response_format == {"type": "json_object"}:
            msgs = msgs + [{
                "role": "system",
                "content": "Reply with ONLY a valid JSON object. No prose, no code fences.",
            }]
        assert self._raw is not None
        return await self._raw.achat(messages=msgs, temperature=temperature,
                                     max_tokens=max_tokens, tools=tools)

    async def structured_completion(
        self,
        messages: List[Dict[str, Any]],
        schema: Dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Prompt-enforced JSON output with fresh-generation retries."""
        msgs = list(messages) + [{
            "role": "system",
            "content": "Reply with ONLY a valid JSON object. No prose, no code fences.",
        }]
        assert self._raw is not None
        last: Exception | None = None
        for attempt in range(3):
            try:
                resp = await self._raw.achat(messages=msgs, temperature=temperature)
                return _extract_json(resp.choices[0].message.content)
            except Exception as exc:
                last = exc
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
        raise RawLLMError(f"structured_completion failed: {last}")


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
