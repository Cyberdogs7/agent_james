"""Qwen3-TTS voices for Agent James (ported from anime `studio/tts_runner.py`).

Two modes, no recording required by default:

- **design** (default): VoiceDesign creates James's voice from a text
  description, per call, through the resident ``--serve`` worker — the same
  pattern anime uses per dialogue line. Voice identity = description string.
- **clone** (opt-in): reference WAV + exact transcript → persisted ``.pt``
  prompt cache (rebuilt only when model/ref-audio/ref-text change), for an
  exact real voice.

The anime project's model venv runs the worker (one JSON op per stdin line),
keeping ONE 1.7B model resident; idle-timeout exits and releases VRAM —
the 16GB discipline (Qwen ~4GB + Whisper ~2GB + optional local LLM).

Output is normalized to 24kHz mono PCM16 for the ``audio_data`` path,
whatever sample rate the model emits.

Env:
  JAMES_TTS_VENV         TTS venv python (default: LanguageLearner/.venv)
  JAMES_TTS_RUNNER       tts_runner.py (default: anime studio/tts_runner.py)
  JAMES_TTS_BASE_MODEL   Qwen3-TTS-12Hz-1.7B-Base dir (clone mode)
  JAMES_TTS_DESIGN_MODEL Qwen3-TTS-12Hz-1.7B-VoiceDesign dir (design mode)
  JAMES_TTS_SOX_DIR      sox bin dir (qwen_tts hard-requires sox on PATH)
  JAMES_TTS_IDLE_TIMEOUT serve idle exit seconds (default 300)
  JAMES_VOICE_FILE       optional voice JSON override. Default: built-in
                         James description below (no file needed).
  JAMES_VOICE_DESCRIPTION  override the designed voice description.

Voice JSON (only needed for clone mode or a custom description):
  {"mode": "design", "voice_description": "warm British male ..."}
  {"mode": "clone", "ref_audio": "C:/audio/voice.wav",
   "ref_text": "exact words in the wav", "language": "English"}
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import wave
from array import array
from pathlib import Path

TARGET_SR = 24000

#: Built-in James voice — no recording needed. VoiceDesign renders this
#: description consistently on every call (same pattern anime uses per line).
DEFAULT_VOICE_DESCRIPTION = (
    "A warm British male voice in his late thirties, calm and articulate, "
    "with a dry understated wit. Measured pace, clear diction, "
    "confident but never hurried."
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_voice_file() -> Path:
    override = os.getenv("JAMES_VOICE_FILE", "")
    if override:
        return Path(override)
    return _repo_root() / "voices" / "james.json"


def load_voice(path: str | Path | None = None) -> dict | None:
    """Resolve the active voice.

    Returns ``{"mode": "design", ...}`` by default (built-in James
    description, overridable via ``JAMES_VOICE_DESCRIPTION`` or a voice file).
    Returns ``{"mode": "clone", ...}`` when the voice file names a valid
    reference WAV. Returns None only when the TTS stack itself is missing
    (checked by ``QwenTTS.is_available``).
    """
    desc_override = os.getenv("JAMES_VOICE_DESCRIPTION", "").strip()
    p = Path(path) if path else default_voice_file()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except OSError:
        d = None
    except ValueError:
        d = None
    if isinstance(d, dict):
        if d.get("mode") == "clone" and d.get("ref_audio"):
            if Path(str(d["ref_audio"])).is_file():
                return {"mode": "clone", "ref_audio": str(d["ref_audio"]),
                        "ref_text": str(d.get("ref_text") or ""),
                        "cache": str(d.get("cache") or (str(d["ref_audio"]) + ".clone.pt")),
                        "language": str(d.get("language") or "English")}
        if d.get("voice_description"):
            return {"mode": "design",
                    "voice_description": str(d["voice_description"]),
                    "language": str(d.get("language") or "English")}
    return {"mode": "design",
            "voice_description": desc_override or DEFAULT_VOICE_DESCRIPTION,
            "language": "English"}


def _resample_mono_pcm16(samples: array, src_sr: int, dst_sr: int = TARGET_SR) -> bytes:
    if src_sr == dst_sr:
        return samples.tobytes()
    n = len(samples)
    m = max(1, round(n * dst_sr / src_sr))
    out = array("h")
    for i in range(m):
        pos = i * n / m
        j = int(pos)
        frac = pos - j
        a = samples[j] if j < n else 0
        b = samples[j + 1] if j + 1 < n else a
        out.append(int(a + (b - a) * frac))
    return out.tobytes()


def _read_reply(proc: subprocess.Popen, max_skips: int = 50) -> dict:
    """Read stdout until the protocol reply (a dict with ``"ok"``).

    Model load prints junk to stdout (masked tokens, warnings, blank lines) —
    same reason anime's adapter skips non-protocol lines. ``""`` means EOF.
    """
    skips = 0
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("Qwen TTS worker exited without reply")
        try:
            obj = json.loads(line)
        except ValueError:
            skips += 1
            if skips > max_skips:
                raise RuntimeError(f"Qwen TTS bad reply: {line[:200]}")
            continue
        if isinstance(obj, dict) and "ok" in obj:
            return obj
        skips += 1
        if skips > max_skips:
            raise RuntimeError(f"Qwen TTS bad reply: {line[:200]}")


def wav_to_pcm24k(path: str | Path) -> bytes:
    """Read a WAV file → 24kHz mono PCM16 bytes (stdlib only)."""
    with wave.open(str(path), "rb") as w:
        nch, sw, sr, nframes = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(nframes)
    if sw == 1:  # 8-bit unsigned → 16-bit
        samples = array("h", ((b - 128) << 8 for b in raw))
    elif sw == 2:
        samples = array("h")
        samples.frombytes(raw)
        if sys.byteorder == "big":
            samples.byteswap()
    else:  # 24/32-bit: take high bytes (good enough for voice preview path)
        step = sw
        samples = array("h")
        for i in range(0, len(raw), step):
            chunk = raw[i:i + step]
            if len(chunk) < step:
                break
            val = int.from_bytes(chunk[-2:], "little", signed=True)
            samples.append(val)
    if nch > 1:  # downmix: average channels
        mono = array("h")
        for i in range(0, len(samples), nch):
            frame = samples[i:i + nch]
            mono.append(sum(frame) // len(frame))
        samples = mono
    return _resample_mono_pcm16(samples, sr)


class QwenTTS:
    """Resident Qwen3-TTS worker (serve mode) with one-shot fallback.

    Design mode needs the VoiceDesign checkpoint; clone mode needs Base.
    The worker loads ONE model at a time (see anime runner ``ensure``).
    """

    def __init__(self):
        self.venv = os.getenv(
            "JAMES_TTS_VENV",
            "C:/Users/Chad/PycharmProjects/LanguageLearner/.venv/Scripts/python.exe",
        )
        self.runner = os.getenv(
            "JAMES_TTS_RUNNER",
            "C:/Users/Chad/PycharmProjects/anime/studio/tts_runner.py",
        )
        self.base_model = os.getenv(
            "JAMES_TTS_BASE_MODEL",
            "C:/Users/Chad/PycharmProjects/LanguageLearner/tts/models/Qwen3-TTS-12Hz-1.7B-Base",
        )
        self.design_model = os.getenv(
            "JAMES_TTS_DESIGN_MODEL",
            "C:/Users/Chad/PycharmProjects/LanguageLearner/tts/models/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        )
        self.sox_dir = os.getenv(
            "JAMES_TTS_SOX_DIR",
            "C:/Users/Chad/AppData/Local/Microsoft/WinGet/Packages/ChrisBagwell.SoX_Microsoft.Winget.Source_8wekyb3d8bbwe/sox-14.4.2",
        )
        self.idle_timeout = int(os.getenv("JAMES_TTS_IDLE_TIMEOUT", "300") or 300)
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        if not (Path(self.venv).is_file() and Path(self.runner).is_file()):
            return False
        voice = load_voice() or {"mode": "design"}
        if voice.get("mode") == "clone":
            return Path(self.base_model).is_dir()
        return Path(self.design_model).is_dir()

    def _spawn(self) -> subprocess.Popen:
        cmd = [self.venv, self.runner, "--serve", "--base-model", self.base_model,
               "--design-model", self.design_model,
               "--idle-timeout", str(self.idle_timeout)]
        if self.sox_dir:
            cmd += ["--sox-dir", self.sox_dir]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, bufsize=1,
                                encoding="utf-8", creationflags=flags)
        # Ping to verify the model venv is functional. Model load prints
        # junk to stdout (masked tokens, warnings) — skip to the protocol reply.
        proc.stdin.write(json.dumps({"op": "ping"}) + "\n")
        proc.stdin.flush()
        reply = _read_reply(proc, max_skips=50)
        if not reply.get("ok"):
            proc.terminate()
            raise RuntimeError(f"Qwen TTS worker ping failed: {reply.get('error', '?')}")
        return proc

    def _ensure_worker(self) -> subprocess.Popen:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return self._proc
            self._proc = self._spawn()
            return self._proc

    def _request(self, payload: dict, timeout: float = 180.0) -> dict:
        proc = self._ensure_worker()
        with self._lock:
            try:
                proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                self._proc = None
                proc = self._ensure_worker()
                proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                proc.stdin.flush()
            try:
                return _read_reply(proc)
            except RuntimeError:
                self._proc = None
                raise

    def stop(self) -> None:
        with self._lock:
            proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()

    def synthesize_sync(self, text: str) -> bytes:
        """Text → 24kHz mono PCM16 bytes (design or clone voice)."""
        voice = load_voice() or {"mode": "design",
                                 "voice_description": DEFAULT_VOICE_DESCRIPTION,
                                 "language": "English"}
        if not self.is_available():
            raise RuntimeError("Qwen TTS venv/model missing.")
        with tempfile.TemporaryDirectory(prefix="james_tts_") as tmp:
            out_wav = str(Path(tmp) / "line.wav")
            try:
                reply = self._request(self._op_for(voice, text, out_wav))
            except Exception:
                # Serve worker failed (e.g. VRAM busy): one-shot fallback.
                self.stop()
                reply = self._oneshot(text, out_wav)
            if not reply.get("ok"):
                raise RuntimeError(f"Qwen TTS failed: {reply.get('error', '?')}")
            return wav_to_pcm24k(out_wav)

    def _op_for(self, voice: dict, text: str, out_wav: str) -> dict:
        if voice.get("mode") == "clone":
            ref_audio = str(voice["ref_audio"])
            return {
                "op": "clone", "text": text,
                "language": voice.get("language") or "English",
                "out": out_wav, "ref_audio": ref_audio,
                "ref_text": voice.get("ref_text") or "",
                "cache": str(voice.get("cache") or (ref_audio + ".clone.pt")),
                "model": self.base_model,
            }
        return {
            "op": "design", "text": text,
            "language": voice.get("language") or "English",
            "instruct": voice.get("voice_description") or DEFAULT_VOICE_DESCRIPTION,
            "out": out_wav,
        }

    def _oneshot(self, text: str, out_wav: str) -> dict:
        """One-shot via a fresh process (slow: reloads 1.7B per call)."""
        voice = load_voice() or {}
        # Reuse the serve protocol through a short-lived worker (single request).
        cmd = [self.venv, self.runner, "--serve", "--base-model", self.base_model,
               "--design-model", self.design_model, "--idle-timeout", "5"]
        if self.sox_dir:
            cmd += ["--sox-dir", self.sox_dir]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                creationflags=flags)
        try:
            proc.stdin.write(json.dumps({"op": "ping"}) + "\n")
            proc.stdin.flush()
            try:
                _read_reply(proc)  # ping reply (skip stdout junk)
            except RuntimeError:
                pass
            proc.stdin.write(json.dumps(
                self._op_for(voice or {"mode": "design",
                                       "voice_description": DEFAULT_VOICE_DESCRIPTION,
                                       "language": "English"},
                             text, out_wav),
                ensure_ascii=False) + "\n")
            proc.stdin.flush()
            try:
                return _read_reply(proc)
            except RuntimeError as e:
                return {"ok": False, "error": str(e)}
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.terminate()

    async def synthesize(self, text: str) -> bytes:
        return await asyncio.to_thread(self.synthesize_sync, text)
