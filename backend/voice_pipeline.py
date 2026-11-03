"""Agent James voice pipeline — local/hybrid replacement for Gemini Native Audio.

Pipeline: VAD-segment → STT → LLM (OpenRouter/LM Studio/Ollama) → sentence-chunk → TTS → audio_data (24kHz).

No hard dependency on google-genai. All heavy STT/TTS imports are lazy/optional
so the backend boots in text-only mode without extra installs.

Recommended local defaults (RTX 4060 Ti 16GB, see docs/ARCHITECTURE.md):
- STT: faster-whisper (distil-large-v3 / large-v3-turbo) + silero-vad gate
- TTS: Qwen3-TTS clone (custom voices) → Kokoro-82M (native 24kHz) → Piper (CPU)
- LLM: backend.llm_client.LLMClient raw httpx (OpenRouter → LM Studio fallback)

ElevenLabs is NOT in this chain. The only ElevenLabs code left in the repo is
the legacy batch audiobook (backend/autonovel/gen_audiobook.py, opt-in).
"""

import os
import re

SAMPLE_IN = 16000
SAMPLE_OUT = 24000


def get_llm():
    """Lazy LLMClient accessor (OpenRouter → LM Studio fallback)."""
    from backend.llm_client import get_llm_client
    return get_llm_client(prefer_openrouter=True)


def split_sentences(text):
    """Split LLM output into speakable chunks for streaming TTS."""
    parts = re.split(r'(?<=[.!?])\s+', (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


class STTProvider:
    """Speech-to-text. Default: unavailable (frontend text input). Opt-in local Whisper."""

    def __init__(self):
        self.backend = os.getenv("JAMES_STT_BACKEND", "none").lower()  # none|faster-whisper
        self.model_name = os.getenv("JAMES_STT_MODEL", "distil-large-v3")
        self._model = None

    def is_available(self):
        if self.backend == "faster-whisper":
            try:
                __import__("faster_whisper")
                return True
            except ImportError:
                return False
        return False

    def transcribe(self, pcm16k_bytes):
        """Transcribe 16kHz mono PCM bytes → text. Raises if backend unavailable."""
        if self.backend != "faster-whisper":
            raise RuntimeError("STT backend not configured (JAMES_STT_BACKEND=none). Use frontend text input.")
        from faster_whisper import WhisperModel
        if self._model is None:
            device = os.getenv("JAMES_STT_DEVICE", "cuda")
            compute = os.getenv("JAMES_STT_COMPUTE", "int8_float16")
            self._model = WhisperModel(self.model_name, device=device, compute_type=compute)
        import numpy as np
        audio = np.frombuffer(pcm16k_bytes, dtype=np.int16).astype("float32") / 32768.0
        segments, _ = self._model.transcribe(audio, vad_filter=True, beam_size=1, condition_on_previous_text=False)
        return "".join(s.text for s in segments).strip()


class TTSProvider:
    """Text-to-speech. Priority: Qwen3-TTS clone → Kokoro local → Piper → none."""

    def __init__(self):
        self.backend = os.getenv("JAMES_TTS_BACKEND", "auto").lower()  # auto|qwen|kokoro|piper|none
        self.voice = os.getenv("JAMES_TTS_VOICE", "af_heart")

    def selected_backend(self):
        if self.backend != "auto":
            return self.backend
        try:
            from backend.qwen_tts import QwenTTS
            if QwenTTS().is_available():
                return "qwen"
        except Exception:
            pass
        try:
            __import__("kokoro")
            return "kokoro"
        except ImportError:
            pass
        try:
            __import__("piper")
            return "piper"
        except ImportError:
            pass
        return "none"

    def is_available(self):
        return self.selected_backend() != "none"

    async def synthesize(self, text):
        """Text → 24kHz mono PCM16 bytes. Returns b"" if no backend."""
        backend = self.selected_backend()
        if backend == "qwen":
            return await self._qwen(text)
        if backend == "kokoro":
            return await self._kokoro(text)
        if backend == "piper":
            return await self._piper(text)
        return b""

    async def _qwen(self, text):
        from backend.qwen_tts import QwenTTS
        return await QwenTTS().synthesize(text)

    async def _kokoro(self, text):
        import asyncio
        def _run():
            from kokoro import KPipeline
            import numpy as np
            pipe = KPipeline(lang_code="a")
            chunks = []
            for _, _, audio in pipe(text, voice=self.voice):
                chunks.append(audio)
            if not chunks:
                return b""
            import numpy as _np
            full = _np.concatenate([_np.asarray(c) for c in chunks])
            pcm = (_np.clip(full, -1.0, 1.0) * 32767).astype(_np.int16)
            return pcm.tobytes()
        return await asyncio.to_thread(_run)

    async def _piper(self, text):
        # Piper outputs 22050Hz by default; resample note left to caller.
        # Kept as stub — wire to piper-tts when installed.
        raise RuntimeError("Piper TTS not wired yet. Install piper-tts and set JAMES_TTS_BACKEND=piper.")
