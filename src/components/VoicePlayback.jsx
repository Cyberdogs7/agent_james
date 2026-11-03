import { useEffect, useRef } from "react";

// Renderless voice output: streams server PCM (24kHz mono int16) over
// Socket.IO and plays it in the browser. Works when frontend and server are
// on different devices — audio travels as socket binary, no server speakers.
const SAMPLE_RATE = 24000;

export default function VoicePlayback({ socket, speakerId, muted }) {
  const ctxRef = useRef(null);
  const queueRef = useRef([]);
  const playingRef = useRef(false);
  const nextStartRef = useRef(0);
  const currentSourceRef = useRef(null);

  const ensureCtx = () => {
    if (!ctxRef.current) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctxRef.current = new AC({ sampleRate: SAMPLE_RATE });
    }
    const ctx = ctxRef.current;
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    if (speakerId && typeof ctx.setSinkId === "function") {
      try {
        ctx.setSinkId(speakerId);
      } catch {
        /* output device select unsupported — default speakers */
      }
    }
    return ctx;
  };

  const stopAll = () => {
    queueRef.current = [];
    try {
      currentSourceRef.current?.stop();
    } catch {
      /* already stopped */
    }
    currentSourceRef.current = null;
    playingRef.current = false;
  };

  const pump = () => {
    if (playingRef.current) return;
    const ctx = ensureCtx();
    if (!ctx) return;
    const chunk = queueRef.current.shift();
    if (!chunk) return;
    playingRef.current = true;
    const buf = ctx.createBuffer(1, chunk.length, SAMPLE_RATE);
    buf.getChannelData(0).set(chunk);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(ctx.destination);
    currentSourceRef.current = src;
    // Gapless-ish: start right when the previous chunk ends.
    const startAt = Math.max(ctx.currentTime + 0.02, nextStartRef.current);
    src.start(startAt);
    nextStartRef.current = startAt + buf.duration;
    src.onended = () => {
      currentSourceRef.current = null;
      playingRef.current = false;
      pump();
    };
  };

  const enqueuePcm = (int16) => {
    const f = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      f[i] = int16[i] / (int16[i] < 0 ? 0x8000 : 0x7fff);
    }
    queueRef.current.push(f);
    pump();
  };

  useEffect(() => {
    if (!socket) return;
    const handleAudio = (data) => {
      try {
        if (muted) return;
        const raw = data?.data ?? data;
        if (raw instanceof ArrayBuffer) {
          enqueuePcm(new Int16Array(raw));
        } else if (ArrayBuffer.isView(raw)) {
          enqueuePcm(
            new Int16Array(raw.buffer, raw.byteOffset, Math.floor(raw.byteLength / 2)),
          );
        } else if (typeof raw === "string") {
          // base64 fallback (some transports don't preserve binary)
          const bin = atob(raw);
          const bytes = new Uint8Array(bin.length);
          for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
          enqueuePcm(new Int16Array(bytes.buffer));
        }
      } catch (e) {
        console.error("[VoicePlayback]", e);
      }
    };
    const handleStatus = (data) => {
      const msg = data?.msg || "";
      if (msg === "Agent interrupted." || msg === "Agent James Stopped") stopAll();
      else if (msg === "Agent James Started") ensureCtx();
    };
    socket.on("audio_data", handleAudio);
    socket.on("status", handleStatus);
    return () => {
      socket.off("audio_data", handleAudio);
      socket.off("status", handleStatus);
    };
  }, [socket, muted, speakerId]);

  // Autoplay policy: browsers need a user gesture before audio plays.
  useEffect(() => {
    const unlock = () => ensureCtx();
    window.addEventListener("pointerdown", unlock);
    return () => {
      window.removeEventListener("pointerdown", unlock);
      stopAll();
      ctxRef.current?.close().catch(() => {});
      ctxRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}
