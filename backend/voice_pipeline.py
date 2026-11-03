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


_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty"}


def _two_digit(n):
    n = int(n)
    if n < 20:
        return _ONES[n]
    tens, ones = (n // 10) * 10, n % 10
    return _TENS[tens] + ("" if ones == 0 else " " + _ONES[ones])


def _ordinal(n):
    n = int(n)
    if n < 20:
        if n in (1, 2, 3):
            return {1: "first", 2: "second", 3: "third"}[n]
        if 10 <= n <= 20:
            return _ONES[n] + "th"
        return _ONES[n] + "th"
    if n < 100:
        last = n % 10
        if last in (1, 2, 3):
            return _two_digit(n - last) + " " + {1: "first", 2: "second", 3: "third"}[last]
        base = _two_digit(n)
        return (base[:-1] + "ieth") if base.endswith("y") else (base + "th")
    return str(n) + "th"


def _year_words(y):
    y = int(y)
    if 2000 <= y < 2010:
        rest = y - 2000
        return "two thousand" if rest == 0 else "two thousand " + _ONES[rest]
    if 2010 <= y < 2100:
        return "twenty " + (_ONES[y - 2000] if y - 2000 < 10 else _two_digit(y - 2000))
    return str(y)


def normalize_for_speech(text):
    """Rewrite LLM text the way it should be SPOKEN.

    TTS models read literally: "11:54 AM" becomes "eleven thousand four".
    Expand times, dates, ordinals, years; strip markdown and symbols.
    """
    t = text or ""
    t = re.sub(r"[*_`#>|]", "", t)  # markdown
    # Times: 11:54 AM / 3:05pm / 12:00 P.M.
    def _time(m):
        h, mi, ap = int(m.group(1)), m.group(2), m.group(3).upper()
        h12 = h % 12 or 12
        hw = _ONES[h12]
        mw = "o'clock" if mi == "00" else ("oh " + _ONES[int(mi)] if mi.startswith("0") else _two_digit(mi))
        return f"{hw} {mw} {'A' if ap == 'A' else 'P'} M"
    t = re.sub(r"\b(\d{1,2}):(\d{2})\s*([AP])\.?\s*M\.?", _time, t)
    # Dates with year: November 3, 2026 -> November third, twenty twenty-six
    def _date(m):
        return f"{m.group(1)} {_ordinal(m.group(2))}, {_year_words(m.group(3))}"
    t = re.sub(r"\b(January|February|March|April|May|June|July|August|September|"
               r"October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", _date, t)
    # Standalone ordinals: 3rd -> third
    t = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", lambda m: _ordinal(m.group(1)), t)
    # Bare years: 2026 -> twenty twenty-six
    t = re.sub(r"\b(20\d{2})\b", lambda m: _year_words(m.group(1)), t)
    # Lone AM/PM -> A M / P M
    t = re.sub(r"\bAM\b", "A M", t)
    t = re.sub(r"\bPM\b", "P M", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def split_speech_chunks(text, per_chunk=2, max_chars=280):
    """Pair sentences into TTS chunks.

    Zero-shot cloners condition per call: single short sentences drift voice
    and reset prosody every few seconds (choppy, morphing). Pairs give each
    call enough context for a stable voice and flowing prosody, at the cost
    of slightly later first audio. Overlong pairs are split back up.
    """
    sents = split_sentences(text)
    chunks, buf = [], []
    for s in sents:
        buf.append(s)
        joined = " ".join(buf)
        if len(buf) >= per_chunk or len(joined) >= max_chars:
            chunks.append(joined)
            buf = []
    # Flush: merge a leftover single sentence into the previous chunk so no
    # call ever goes out with a bare short sentence (worst for voice drift).
    if buf:
        leftover = " ".join(buf)
        if chunks and len(buf) < per_chunk:
            chunks[-1] = (chunks[-1] + " " + leftover).strip()
        else:
            chunks.append(leftover)
    return chunks


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
    """Text-to-speech. Priority: Chatterbox clone → Qwen → Kokoro → Piper → none.

    Chatterbox is the realtime backend (~1.5s/chunk, James's cloned voice);
    Qwen is the slower quality path (2.4s/chunk, designed/cloned voice).
    """

    def __init__(self):
        self.backend = os.getenv("JAMES_TTS_BACKEND", "auto").lower()  # auto|chatterbox|qwen|kokoro|piper|none
        self.voice = os.getenv("JAMES_TTS_VOICE", "af_heart")

    def selected_backend(self):
        if self.backend != "auto":
            return self.backend
        try:
            from backend.chatterbox_tts import is_available as _cb
            if _cb():
                return "chatterbox"
        except Exception:
            pass
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
        if backend == "chatterbox":
            return await self._chatterbox(text)
        if backend == "qwen":
            return await self._qwen(text)
        if backend == "kokoro":
            return await self._kokoro(text)
        if backend == "piper":
            return await self._piper(text)
        return b""

    async def _chatterbox(self, text):
        from backend.chatterbox_tts import synthesize as _synth
        return await _synth(text)

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
