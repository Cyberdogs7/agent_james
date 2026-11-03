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
    """Optional OpenAI-compatible embeddings. Returns None if unconfigured."""
    base_url = os.getenv("OPENAI_EMBED_BASE_URL", "")
    model = os.getenv("OPENAI_EMBED_MODEL", "")
    api_key = os.getenv("OPENAI_EMBED_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    if not base_url or not model:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key or "local", base_url=base_url)
        res = await client.embeddings.create(model=model, input=text)
        return list(res.data[0].embedding)
    except Exception:
        return None


def embed_sync(text):
    """Sync embedding for MemoryManager. Uses local hashing (no network)."""
    if not (text or "").strip():
        return None
    return local_embed(text)
