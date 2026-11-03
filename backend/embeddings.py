"""Local-first embeddings replacement for text-embedding-004.

Default: hashed bag-of-words vectors (no network, no google-genai).
Optional: OpenAI-compatible embeddings via OPENAI_EMBED_BASE_URL + OPENAI_EMBED_MODEL.
MemoryManager.search_memory already falls back to keyword overlap when
embeddings are None, so returning None is always safe.
"""

import hashlib
import math
import os

DIM = 256


def local_embed(text):
    vec = [0.0] * DIM
    for token in (text or "").lower().split():
        h = int(hashlib.md5(token.encode()).hexdigest(), 16) % DIM
        vec[h] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


async def api_embed(text):
    """Optional OpenAI-compatible embeddings via raw httpx. None if unconfigured."""
    import httpx
    base_url = os.getenv("OPENAI_EMBED_BASE_URL", "").rstrip("/")
    model = os.getenv("OPENAI_EMBED_MODEL", "")
    api_key = os.getenv("OPENAI_EMBED_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    if not base_url or not model:
        return None
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{base_url}/embeddings",
                                     json={"model": model, "input": text},
                                     headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return list((data.get("data") or [{}])[0].get("embedding") or [])
    except Exception:
        return None


def embed_sync(text):
    """Sync embedding for MemoryManager. Uses local hashing (no network)."""
    if not (text or "").strip():
        return None
    return local_embed(text)
