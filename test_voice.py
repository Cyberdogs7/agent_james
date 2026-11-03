"""Voice pipeline test: text → (LLM) → TTS → your speakers.

Usage (from repo root, .venv python):
    .venv/Scripts/python.exe test_voice.py "Hello James, say something"
    .venv/Scripts/python.exe test_voice.py --chat        # interactive LLM+TTS loop
    .venv/Scripts/python.exe test_voice.py --backends   # show resolved STT/TTS chain

Say mode: synthesizes the text with the active TTS backend and plays it.
Chat mode: needs an LLM (OPENROUTER_API_KEY or LM Studio running) — replies
are spoken sentence-by-sentence through the realtime clone.
Saves every reply to voices/test_out.wav as well.
"""
import asyncio
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT_WAV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices", "test_out.wav")


def save_wav(pcm: bytes, path: str = OUT_WAV, sr: int = 24000):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    print(f"[test] saved {path} ({len(pcm) / 2 / sr:.1f}s @ {sr}Hz)")


def play_wav(path: str = OUT_WAV):
    try:
        import winsound
        print("[test] playing through speakers...")
        winsound.PlaySound(path, winsound.SND_FILENAME)
    except Exception as e:
        print(f"[test] autoplay unavailable ({e}) — play {path} manually.")


async def say(text: str, play: bool = True):
    from backend.voice_pipeline import TTSProvider, split_sentences
    tts = TTSProvider()
    print(f"[test] TTS backend: {tts.selected_backend()}")
    if not tts.is_available():
        print("[test] No TTS backend available. Chatterbox needs voices/james_ref.wav + torch/CUDA.")
        return
    full = b""
    for i, chunk in enumerate(split_sentences(text), 1):
        print(f"[test] synth chunk {i}: {chunk[:60]}...")
        pcm = await tts.synthesize(chunk)
        full += pcm
    if not full:
        print("[test] Got no audio back.")
        return
    save_wav(full)
    if play:
        play_wav()


async def chat():
    from backend.llm_client import get_llm_client
    from backend.voice_pipeline import TTSProvider, split_sentences
    try:
        llm = get_llm_client(prefer_openrouter=True)
    except Exception as e:
        print(f"[test] LLM unavailable: {e}")
        return
    tts = TTSProvider()
    print(f"[test] LLM provider: {llm.provider} | model: {llm.model}")
    print(f"[test] TTS backend: {tts.selected_backend()}")
    print("Type something (quit/exit/q to stop).")
    while True:
        try:
            user = await asyncio.to_thread(input, "\nYou: ")
        except (EOFError, KeyboardInterrupt):
            break
        if user.strip().lower() in ("quit", "exit", "q"):
            break
        if not user.strip():
            continue
        try:
            resp = await llm.chat_completion(
                messages=[
                    {"role": "system", "content": "You are James, a witty British voice assistant. Keep replies to 2-3 short sentences (they will be spoken aloud)."},
                    {"role": "user", "content": user},
                ],
                temperature=0.7,
            )
            reply = resp.choices[0].message.content or ""
        except Exception as e:
            print(f"[test] LLM error: {e}")
            continue
        print(f"\nJames: {reply}")
        full = b""
        for chunk in split_sentences(reply):
            try:
                full += await tts.synthesize(chunk)
            except Exception as e:
                print(f"[test] TTS chunk failed: {e}")
        if full:
            save_wav(full)
            play_wav()


def show_backends():
    from backend.voice_pipeline import TTSProvider, STTProvider
    from backend.chatterbox_tts import is_available as cb, default_ref
    from backend.qwen_tts import QwenTTS
    print(f"STT backend:      {STTProvider().backend}")
    print(f"TTS backend:      {TTSProvider().selected_backend()}")
    print(f"clone ref:        {default_ref()} ({'found' if default_ref().is_file() else 'MISSING'})")
    print(f"chatterbox ready: {cb()}")
    try:
        print(f"qwen ready:       {QwenTTS().is_available()}")
    except Exception as e:
        print(f"qwen ready:       False ({e})")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    args = sys.argv[1:]
    if args and args[0] == "--chat":
        asyncio.run(chat())
    elif args and args[0] == "--backends":
        show_backends()
    else:
        text = " ".join(args) if args else "Hello. I am James. The realtime voice pipeline is working."
        asyncio.run(say(text))
