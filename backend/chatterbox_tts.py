"""Chatterbox realtime voice clone for Agent James (MIT-licensed).

Zero-shot clone from the Qwen-designed reference (``voices/james_ref.wav``):
no training, ~500M params, native 24kHz output — matches the ``audio_data``
path with no resampling. ~1.5s per sentence chunk on RTX 4060 Ti (vs 2.4s
Qwen); sentence-chunk streaming + overlap (synthesize N+1 while playing N)
gives continuous speech. True sub-second would need a smaller model —
Kokoro stays the speed fallback (fixed voices).

Notes:
- Resemble's inaudible watermark is deliberately disabled (DummyWatermarker
  passthrough): the installed perth 1.0.1 can't load its net module anyway
  (needs the removed ``pkg_resources``), and we don't watermark James's voice.
- Model is a process-wide singleton (loads once, ~2GB VRAM). Pair with an
  OpenRouter LLM to avoid VRAM contention with a local LLM.

Env:
  JAMES_VOICE_REF    clone reference wav (default: voices/james_ref.wav)
  JAMES_CB_DEVICE    cuda|cpu (default cuda)
  JAMES_CB_EXAGGERATION  emotion intensity 0-1 (default 0.5)
  JAMES_CB_CFG       guidance weight (default 0.5)
  JAMES_CB_TEMPERATURE sampling temperature (default 0.3 — lower = steadier
                         voice across chunks; 0.8 default drifts per call)
"""
from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path

TARGET_SR = 24000


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_ref() -> Path:
    override = os.getenv("JAMES_VOICE_REF", "")
    if override:
        return Path(override)
    return _repo_root() / "voices" / "james_ref.wav"


_MODEL = None
_MODEL_LOCK = threading.Lock()


def _load_model(device: str):
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        import perth
        # See module docstring: no third-party watermark on our own voice.
        if getattr(perth, "PerthImplicitWatermarker", None) is None:
            perth.PerthImplicitWatermarker = perth.DummyWatermarker
        from chatterbox.tts import ChatterboxTTS
        _MODEL = ChatterboxTTS.from_pretrained(device=device)
        return _MODEL


def is_available() -> bool:
    if not default_ref().is_file():
        return False
    try:
        __import__("chatterbox.tts")
        return True
    except ImportError:
        return False


def synthesize_sync(text: str) -> bytes:
    """Text → 24kHz mono PCM16 bytes in James's cloned voice."""
    ref = default_ref()
    if not ref.is_file():
        raise RuntimeError("Clone reference missing (voices/james_ref.wav).")
    device = os.getenv("JAMES_CB_DEVICE", "cuda")
    model = _load_model(device)
    try:
        import torch
        if device == "cuda" and torch.cuda.is_available():
            model.device = "cuda"
    except Exception:
        pass
    wav = model.generate(
        text,
        audio_prompt_path=str(ref),
        exaggeration=float(os.getenv("JAMES_CB_EXAGGERATION", "0.5") or 0.5),
        cfg_weight=float(os.getenv("JAMES_CB_CFG", "0.5") or 0.5),
        temperature=float(os.getenv("JAMES_CB_TEMPERATURE", "0.3") or 0.3),
    )
    import numpy as np
    audio = np.asarray(wav.squeeze().cpu() if hasattr(wav, "cpu") else wav,
                       dtype=np.float32)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    return pcm.tobytes()


async def synthesize(text: str) -> bytes:
    return await asyncio.to_thread(synthesize_sync, text)
