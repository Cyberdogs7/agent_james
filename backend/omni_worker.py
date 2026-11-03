"""Resident OmniVoice worker (runs under the Omni venv, NOT .venv).

Speaks the anime tts_runner serve protocol (one JSON op per stdin line):
  {"op": "ping"} -> {"ok": true}
  {"op": "synth", "text": ..., "out": path} -> {"ok": true} | {"ok": false, ...}
Exits on stdin EOF or after --idle-timeout seconds without a request
(releases VRAM; the parent respawns on demand).

Usage:
  <omni-venv>/python.exe backend/omni_worker.py --serve \\
      --ref-audio voices/james_ref_short.wav --ref-text "..." \\
      --cache voices/james.pt [--idle-timeout 300]
"""
import argparse
import json
import sys
import time

import torch


def _reply(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true", required=True)
    ap.add_argument("--ref-audio", default="")
    ap.add_argument("--ref-text", default="")
    ap.add_argument("--cache", default="")
    ap.add_argument("--model", default="k2-fsa/OmniVoice")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--idle-timeout", type=float, default=300.0)
    args = ap.parse_args()

    import soundfile as sf
    from omnivoice import OmniVoice, VoiceClonePrompt

    model = OmniVoice.from_pretrained(args.model, device_map=args.device,
                                      dtype=torch.float16)
    prompt = None
    if args.cache:
        import os
        if os.path.isfile(args.cache):
            try:
                prompt = VoiceClonePrompt.load(args.cache)
            except Exception:
                prompt = None
        if prompt is None and args.ref_audio:
            prompt = model.create_voice_clone_prompt(
                ref_audio=args.ref_audio, ref_text=args.ref_text or None)
            try:
                prompt.save(args.cache)
            except Exception:
                pass

    import os as _os
    import threading as _threading

    last = [time.time()]

    def _watchdog():
        while True:
            time.sleep(10)
            if args.idle_timeout > 0 and (time.time() - last[0]) > args.idle_timeout:
                _os._exit(0)

    _threading.Thread(target=_watchdog, daemon=True).start()

    for line in sys.stdin:
        last[0] = time.time()
        try:
            req = json.loads(line)
        except ValueError:
            continue
        op = req.get("op")
        if op == "ping":
            _reply({"ok": True})
            continue
        if op == "synth":
            try:
                text = req.get("text", "")
                out = req.get("out", "")
                if prompt is not None:
                    wav = model.generate(text=text, voice_clone_prompt=prompt)
                else:
                    wav = model.generate(text=text, ref_audio=args.ref_audio or None,
                                         ref_text=args.ref_text or None)
                sf.write(out, wav[0], 24000)
                _reply({"ok": True})
            except Exception as e:  # noqa: BLE001 — must reply, never crash
                _reply({"ok": False, "error": str(e)[:300]})
            continue
        _reply({"ok": False, "error": f"unknown op {op!r}"})


if __name__ == "__main__":
    main()
