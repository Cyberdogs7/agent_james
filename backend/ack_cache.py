"""Instant latency cover: pre-rendered ack clips in James's voice.

The talker LLM + TTS render takes seconds — useless as cover. These clips
render once (warming the voice model as a side effect) and play in ~0ms
while the real pipeline works. Memory: ~6 clips x ~2s x 48KB/s ≈ 600KB.
"""
from __future__ import annotations

import asyncio
import random
import threading

# Kept small on purpose: the warm pass runs at power-on and each clip costs
# a full TTS render (slow while the GPU is shared). 3 clips ≈ ready in ~10s.
ACK_PHRASES = [
    "On it.",
    "Checking now.",
    "Right away, Sir.",
]

_cache: list[bytes] = []
_lock = threading.Lock()
_warming = False


def get_ack_pcm() -> bytes | None:
    """A random pre-rendered ack, or None if the cache is still warming."""
    with _lock:
        if not _cache:
            return None
        return random.choice(_cache)


def is_ready() -> bool:
    with _lock:
        return bool(_cache)


async def _render_all() -> None:
    try:
        from backend.voice_pipeline import TTSProvider
    except ImportError:
        try:
            from voice_pipeline import TTSProvider
        except ImportError:
            return
    try:
        tts = TTSProvider()
        if not tts.is_available():
            return
        rendered = []
        for phrase in ACK_PHRASES:
            try:
                pcm = await tts.synthesize(phrase)
            except Exception:
                continue
            if pcm:
                rendered.append(pcm)
        with _lock:
            _cache.clear()
            _cache.extend(rendered)
    except Exception:
        pass


async def warm_async() -> bool:
    """Pre-render acks (also pre-loads the TTS model). Returns True if ready."""
    await _render_all()
    return is_ready()


def warm_in_background() -> None:
    """Fire-and-forget pre-render (also pre-warms the TTS model). Idempotent."""
    global _warming
    with _lock:
        if _warming or _cache:
            return
        _warming = True

    def _run():
        global _warming
        try:
            asyncio.run(_render_all())
        except Exception:
            pass
        finally:
            with _lock:
                _warming = False

    threading.Thread(target=_run, name="ack-warm", daemon=True).start()
