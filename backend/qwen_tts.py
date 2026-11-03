"""Qwen3-TTS voice cloning for Agent James (ported from anime `studio/tts_runner.py`).

Clone = reference WAV + exact transcript → persisted ``.pt`` prompt cache
(rebuilt only when model/ref-audio/ref-text change). The anime project's
model venv runs a resident ``--serve`` worker (one JSON op per stdin line),
keeping ONE 1.7B model resident; idle-timeout exits and releases VRAM —
the 16GB discipline (Qwen ~4GB + Whisper ~2GB + optional local LLM).

Output is normalized to 24kHz mono PCM16 for the ``audio_data`` path,
whatever sample rate the model emits.

Env:
  JAMES_TTS_VENV         TTS venv python (default: LanguageLearner/.venv)
  JAMES_TTS_RUNNER       tts_runner.py (default: anime studio/tts_runner.py)
  JAMES_TTS_BASE_MODEL   Qwen3-TTS-12Hz-1.7B-Base dir
  JAMES_TTS_SOX_DIR      sox bin dir (qwen_tts hard-requires sox on PATH)
  JAMES_TTS_IDLE_TIMEOUT serve idle exit seconds (default 300)
  JAMES_VOICE_FILE       voice JSON {ref_audio, ref_text, language} for James.
                         Default: <repo>/voices/james.json (see voices/README).

Voice JSON example:
  {"ref_audio": "C:/audio/james_ref.wav", "ref_text": "exact words in the wav",
   "language": "English"}
Record ~10-30s of clean speech + its exact transcript. Until configured,
TTSProvider falls through to Kokoro/Piper.
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_voice_file() -> Path:
    override = os.getenv("JAMES_VOICE_FILE", "")
    if override:
        return Path(override)
    return _repo_root() / "voices" / "james.json"


def load_voice(path: str | Path | None = None) -> dict | None:
    """Load voice JSON; None when unconfigured/invalid."""
    p = Path(path) if path else default_voice_file()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except OSError:
        return None
    except ValueError:
        return None
    if not isinstance(d, dict) or not d.get("ref_audio"):
        return None
    if not Path(str(d["ref_audio"])).is_file():
        return None
    return d


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
    """Resident Qwen3-TTS clone worker (serve mode) with one-shot fallback."""

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
        self.sox_dir = os.getenv(
            "JAMES_TTS_SOX_DIR",
            "C:/Users/Chad/AppData/Local/Microsoft/WinGet/Packages/ChrisBagwell.SoX_Microsoft.Winget.Source_8wekyb3d8bbwe/sox-14.4.2",
        )
        self.idle_timeout = int(os.getenv("JAMES_TTS_IDLE_TIMEOUT", "300") or 300)
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        if not (Path(self.venv).is_file() and Path(self.runner).is_file()
                and Path(self.base_model).is_dir()):
            return False
        return load_voice() is not None

    def _spawn(self) -> subprocess.Popen:
        cmd = [self.venv, self.runner, "--serve", "--base-model", self.base_model,
               "--idle-timeout", str(self.idle_timeout)]
        if self.sox_dir:
            cmd += ["--sox-dir", self.sox_dir]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, bufsize=1,
                                encoding="utf-8", creationflags=flags)
        # Ping to verify the model venv is functional.
        proc.stdin.write(json.dumps({"op": "ping"}) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if '"ok": true' not in line:
            proc.terminate()
            raise RuntimeError(f"Qwen TTS worker ping failed: {line[:200]}")
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
            line = proc.stdout.readline()
        if not line:
            self._proc = None
            raise RuntimeError("Qwen TTS worker exited without reply")
        try:
            return json.loads(line)
        except ValueError:
            raise RuntimeError(f"Qwen TTS bad reply: {line[:200]}")

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
        """Text → 24kHz mono PCM16 bytes (clone voice). Raises when unavailable."""
        voice = load_voice()
        if voice is None:
            raise RuntimeError("Qwen clone voice unconfigured (see voices/james.json).")
        if not self.is_available():
            raise RuntimeError("Qwen TTS venv/model missing.")
        ref_audio = str(voice["ref_audio"])
        cache = str(voice.get("cache") or (ref_audio + ".clone.pt"))
        with tempfile.TemporaryDirectory(prefix="james_tts_") as tmp:
            out_wav = str(Path(tmp) / "line.wav")
            try:
                reply = self._request({
                    "op": "clone", "text": text,
                    "language": voice.get("language") or "English",
                    "out": out_wav, "ref_audio": ref_audio,
                    "ref_text": voice.get("ref_text") or "",
                    "cache": cache, "model": self.base_model,
                })
            except Exception:
                # Serve worker failed (e.g. VRAM busy): one-shot fallback.
                self.stop()
                reply = self._oneshot(text, out_wav)
            if not reply.get("ok"):
                raise RuntimeError(f"Qwen TTS failed: {reply.get('error', '?')}")
            return wav_to_pcm24k(out_wav)

    def _oneshot(self, text: str, out_wav: str) -> dict:
        """One-shot clone via a fresh process (slow: reloads 1.7B per call)."""
        voice = load_voice() or {}
        cache = str(voice.get("cache") or (str(voice.get("ref_audio")) + ".clone.pt"))
        # Reuse the serve protocol through a short-lived worker (single request).
        cmd = [self.venv, self.runner, "--serve", "--base-model", self.base_model,
               "--idle-timeout", "5"]
        if self.sox_dir:
            cmd += ["--sox-dir", self.sox_dir]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                creationflags=flags)
        try:
            proc.stdin.write(json.dumps({"op": "ping"}) + "\n")
            proc.stdin.flush()
            proc.stdout.readline()
            proc.stdin.write(json.dumps({
                "op": "clone", "text": text,
                "language": voice.get("language") or "English",
                "out": out_wav, "ref_audio": str(voice.get("ref_audio")),
                "ref_text": voice.get("ref_text") or "",
                "cache": cache, "model": self.base_model,
            }, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            try:
                return json.loads(line) if line else {"ok": False, "error": "no reply"}
            except ValueError:
                return {"ok": False, "error": f"bad reply: {line[:200]}"}
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
