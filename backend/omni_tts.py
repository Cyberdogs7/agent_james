"""OmniVoice realtime voice for Agent James (trial winner).

Zero-shot clone of the trimmed James ref (10s) with a frozen prompt cache:
stable voice, ~1.3s/chunk, lowest VRAM of the GPU options. The model lives
in its OWN venv (torch cu128); this module only manages a resident
``omni_worker.py`` subprocess (serve protocol, idle-timeout releases VRAM).
See backend/omni_worker.py. Stdlib only in here.

Env:
  JAMES_OMNI_VENV     omni venv python (has omnivoice + torch/cuda)
  JAMES_OMNI_WORKER   worker script (default: backend/omni_worker.py)
  JAMES_OMNI_REF      clone ref wav (default: voices/james_ref_short.wav)
  JAMES_OMNI_REF_TEXT ref transcript (default: voices/james_ref_short.txt)
  JAMES_OMNI_CACHE    voice prompt cache (default: voices/james.pt, gitignored)
  JAMES_OMNI_IDLE     worker idle exit seconds (default 300)
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path

TARGET_SR = 24000


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


class OmniTTS:
    """Resident OmniVoice worker (serve mode) with one-shot fallback."""

    def __init__(self):
        _default_venv = str(_repo_root() / "tts-venv" / "Scripts" / "python.exe")
        self.venv = os.getenv("JAMES_OMNI_VENV", _default_venv)
        default_worker = str(_repo_root() / "backend" / "omni_worker.py")
        self.worker = os.getenv("JAMES_OMNI_WORKER", default_worker)
        default_ref = str(_repo_root() / "voices" / "james_ref_short.wav")
        self.ref_audio = os.getenv("JAMES_OMNI_REF", default_ref)
        default_txt = str(_repo_root() / "voices" / "james_ref_short.txt")
        self.ref_text = ""
        try:
            self.ref_text = Path(os.getenv("JAMES_OMNI_REF_TEXT", default_txt)).read_text(
                encoding="utf-8").strip()
        except OSError:
            self.ref_text = ""
        default_cache = str(_repo_root() / "voices" / "james.pt")
        self.cache = os.getenv("JAMES_OMNI_CACHE", default_cache)
        self.idle_timeout = float(os.getenv("JAMES_OMNI_IDLE", "300") or 300)
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        return (Path(self.venv).is_file() and Path(self.worker).is_file()
                and Path(self.ref_audio).is_file())

    def _spawn(self) -> subprocess.Popen:
        cmd = [self.venv, self.worker, "--serve",
               "--ref-audio", self.ref_audio, "--ref-text", self.ref_text,
               "--cache", self.cache, "--idle-timeout", str(self.idle_timeout)]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, bufsize=1,
                                encoding="utf-8", creationflags=flags)
        from backend.qwen_tts import _read_reply
        proc.stdin.write(json.dumps({"op": "ping"}) + "\n")
        proc.stdin.flush()
        reply = _read_reply(proc)
        if not reply.get("ok"):
            proc.terminate()
            raise RuntimeError(f"Omni worker ping failed: {reply.get('error', '?')}")
        return proc

    def _ensure_worker(self) -> subprocess.Popen:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return self._proc
            self._proc = self._spawn()
            return self._proc

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
        """Text → 24kHz mono PCM16 bytes in James's voice."""
        if not self.is_available():
            raise RuntimeError("Omni TTS unavailable (venv/worker/ref missing).")
        from backend.qwen_tts import _read_reply, wav_to_pcm24k
        with tempfile.TemporaryDirectory(prefix="james_omni_") as tmp:
            out_wav = str(Path(tmp) / "line.wav")
            proc = self._ensure_worker()
            with self._lock:
                try:
                    proc.stdin.write(json.dumps({"op": "synth", "text": text,
                                                 "out": out_wav},
                                                ensure_ascii=False) + "\n")
                    proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    self._proc = None
                    proc = self._ensure_worker()
                    proc.stdin.write(json.dumps({"op": "synth", "text": text,
                                                 "out": out_wav},
                                                ensure_ascii=False) + "\n")
                    proc.stdin.flush()
                try:
                    reply = _read_reply(proc)
                except RuntimeError:
                    self._proc = None
                    raise
            if not reply.get("ok"):
                raise RuntimeError(f"Omni TTS failed: {reply.get('error', '?')}")
            return wav_to_pcm24k(out_wav)

    async def synthesize(self, text: str) -> bytes:
        return await asyncio.to_thread(self.synthesize_sync, text)


_MANAGER: OmniTTS | None = None
_MANAGER_LOCK = threading.Lock()


def _manager() -> OmniTTS:
    """Process-wide singleton: one resident worker, no reload per chunk."""
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            _MANAGER = OmniTTS()
        return _MANAGER


def is_available() -> bool:
    try:
        return _manager().is_available()
    except Exception:
        return False


async def synthesize(text: str) -> bytes:
    return await _manager().synthesize(text)
