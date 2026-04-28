import React, { useEffect, useRef, useState, useMemo } from "react";
import { X } from "lucide-react";

const VISUALIZER_MODES = [
  "spectrum",
  "oscilloscope",
  "bars",
  "wave",
  "circular",
  "mirrored"
];

const WinampVisualizer = ({ socket, onClose }) => {
  const canvasRef = useRef(null);
  const [visData, setVisData] = useState(new Array(64).fill(0));
  const [status, setStatus] = useState({ status: "stopped", track: null });
  const [mode, setMode] = useState("spectrum"); // 'spectrum' or 'oscilloscope'
  const animationRef = useRef(null);
  const dataRef = useRef(new Array(64).fill(0));
  const smoothDataRef = useRef(new Array(64).fill(0));
  const containerRef = useRef(null);
  const lyricsRef = useRef(null);

  useEffect(() => {
    if (!socket) return;

    const onVisData = (payload) => {
      // payload.data is array of ints 0-255
      dataRef.current = payload.data;
    };

    const onStatus = (payload) => {
      console.log("[Winamp] Status:", payload);
      setStatus(payload);
    };

    socket.on("music_vis_data", onVisData);
    socket.on("music_status", onStatus);

    return () => {
      socket.off("music_vis_data", onVisData);
      socket.off("music_status", onStatus);
    };
  }, [socket]);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        if (entry.target === container) {
          canvas.width = entry.contentRect.width;
          canvas.height = entry.contentRect.height;
        }
      }
    });

    resizeObserver.observe(container);

    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      const targetData = dataRef.current;
      const smoothData = smoothDataRef.current;

      // Apply linear interpolation
      const lerpFactor = 0.2;
      for (let i = 0; i < targetData.length; i++) {
        smoothData[i] += (targetData[i] - smoothData[i]) * lerpFactor;
      }

      const data = smoothData;

      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, w, h);

      if (mode === "spectrum") {
        const barWidth = w / data.length;

        for (let i = 0; i < data.length; i++) {
          const value = data[i];
          const percent = value / 255;
          const barHeight = percent * h;

          // Winamp Colors: Green -> Yellow -> Red
          // Simple gradient approximation
          let color = "#00FF00"; // Green
          if (percent > 0.5) color = "#FFFF00"; // Yellow
          if (percent > 0.8) color = "#FF0000"; // Red

          ctx.fillStyle = color;
          ctx.fillRect(i * barWidth, h - barHeight, barWidth - 1, barHeight);

          // Peak (simple white dot)
          ctx.fillStyle = "#FFFFFF";
          ctx.fillRect(i * barWidth, h - barHeight - 2, barWidth - 1, 1);
        }
      } else if (mode === "oscilloscope") {
        ctx.beginPath();
        ctx.strokeStyle = "#00FF00";
        ctx.lineWidth = 2;

        const sliceWidth = (w * 1.0) / data.length;
        let x = 0;

        for (let i = 0; i < data.length; i++) {
          const v = data[i] / 128.0; // 0-255 -> 0-2 roughly
          const y = (v * h) / 2;

          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);

          x += sliceWidth;
        }
        ctx.stroke();
      } else if (mode === "bars") {
        const barWidth = w / data.length;
        const gap = 2;

        for (let i = 0; i < data.length; i++) {
          const value = data[i];
          const percent = value / 255;
          const barHeight = percent * h;

          const numBlocks = Math.floor(barHeight / 5);
          for (let j = 0; j < numBlocks; j++) {
            let color = "#00FF00";
            if (j > numBlocks * 0.5) color = "#FFFF00";
            if (j > numBlocks * 0.8) color = "#FF0000";
            ctx.fillStyle = color;
            ctx.fillRect(i * barWidth, h - (j * 5) - 4, barWidth - gap, 4);
          }
        }
      } else if (mode === "wave") {
        ctx.beginPath();
        ctx.strokeStyle = "#FFFF00";
        ctx.lineWidth = 3;

        ctx.moveTo(0, h);
        const sliceWidth = w / data.length;

        for (let i = 0; i < data.length; i++) {
          const percent = data[i] / 255;
          const y = h - (percent * h);
          const x = i * sliceWidth;

          if (i === 0) ctx.moveTo(x, y);
          else {
            const prevX = (i - 1) * sliceWidth;
            const prevY = h - ((data[i-1] / 255) * h);
            const cpX = prevX + (x - prevX) / 2;
            ctx.quadraticCurveTo(cpX, prevY, x, y);
          }
        }
        ctx.stroke();
      } else if (mode === "circular") {
        const centerX = w / 2;
        const centerY = h / 2;
        const radius = Math.min(centerX, centerY) * 0.4;

        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = "#444444";
        ctx.stroke();

        const angleStep = (2 * Math.PI) / data.length;

        for (let i = 0; i < data.length; i++) {
          const value = data[i];
          const percent = value / 255;
          const barHeight = percent * (Math.min(w, h) / 2 - radius);

          const angle = i * angleStep;

          const startX = centerX + Math.cos(angle) * radius;
          const startY = centerY + Math.sin(angle) * radius;

          const endX = centerX + Math.cos(angle) * (radius + barHeight);
          const endY = centerY + Math.sin(angle) * (radius + barHeight);

          let color = "#00FF00";
          if (percent > 0.5) color = "#FFFF00";
          if (percent > 0.8) color = "#FF0000";

          ctx.beginPath();
          ctx.moveTo(startX, startY);
          ctx.lineTo(endX, endY);
          ctx.strokeStyle = color;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      } else if (mode === "mirrored") {
        const barWidth = w / data.length;
        const centerY = h / 2;

        for (let i = 0; i < data.length; i++) {
          const value = data[i];
          const percent = value / 255;
          const barHeight = percent * (h / 2);

          let color = "#00FF00";
          if (percent > 0.5) color = "#FFFF00";
          if (percent > 0.8) color = "#FF0000";

          ctx.fillStyle = color;
          // Draw top half
          ctx.fillRect(i * barWidth, centerY - barHeight, barWidth - 1, barHeight);
          // Draw bottom half
          ctx.fillRect(i * barWidth, centerY, barWidth - 1, barHeight);
        }
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [mode]);

  const lyricLines = useMemo(() => {
    return status.track?.lyrics?.split("\n") || [];
  }, [status.track?.lyrics]);

  const activeLineIndex = useMemo(() => {
    if (status.track?.progress !== undefined && status.track?.duration && lyricLines.length > 0) {
      const percent = Math.min(1, Math.max(0, status.track.progress / status.track.duration));
      // calculate which line we are on
      // e.g. percent 0.5 with 10 lines -> 5
      return Math.min(lyricLines.length - 1, Math.floor(percent * lyricLines.length));
    }
    return 0;
  }, [status.track?.progress, status.track?.duration, lyricLines.length]);

  useEffect(() => {
    const container = lyricsRef.current;
    if (container && lyricLines.length > 0) {
      const activeChild = container.children[activeLineIndex];
      if (activeChild) {
        const scrollTarget = activeChild.offsetTop - container.clientHeight / 2 + activeChild.clientHeight / 2;

        container.scrollTo({
          top: scrollTarget,
          behavior: "smooth",
        });
      }
    }
  }, [activeLineIndex, lyricLines.length]);

  return (
    <div className="flex flex-col h-full bg-[#1a1a1a] text-[#00FF00] font-mono text-xs select-none pb-1">
      {/* Header / Title Bar */}
      <div
        data-drag-handle
        className="h-5 bg-[#2d2d2d] flex items-center justify-between px-2 cursor-grab active:cursor-grabbing border-b border-[#4a4a4a]"
      >
        <div className="flex items-center gap-1">
          <span className="text-[#cbced0]">WINAMP</span>
          <span className="text-[#00FF00] animate-pulse">⚡</span>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() =>
              setMode((m) => {
                const currentIndex = VISUALIZER_MODES.indexOf(m);
                return VISUALIZER_MODES[(currentIndex + 1) % VISUALIZER_MODES.length];
              })
            }
            className="hover:text-white"
            title="Toggle Mode"
            aria-label="Toggle Mode"
          >
            M
          </button>
          <button
            onClick={onClose}
            className="hover:text-white"
            title="Close"
            aria-label="Close"
          >
            <X size={10} />
          </button>
        </div>
      </div>

      {/* Main Display */}
      <div
        ref={containerRef}
        className="flex-1 relative border border-[#4a4a4a] m-1 bg-black overflow-hidden"
      >
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          onClick={() =>
            setMode((m) => {
              const currentIndex = VISUALIZER_MODES.indexOf(m);
              return VISUALIZER_MODES[(currentIndex + 1) % VISUALIZER_MODES.length];
            })
          }
        />

        {/* Track Info Overlay */}
        <div className="absolute top-1 left-1 text-[#00FF00] bg-black/50 px-1">
          {status.track
            ? `${status.track.title} (${status.status})`
            : "No Track Loaded"}
        </div>

        {/* Bitrate / Time placeholder */}
        <div className="absolute bottom-1 right-1 text-[#00FF00] bg-black/50 px-1">
          {status.status === "playing" ? "128 kbps" : ""}
        </div>

        {/* Lyrics Display */}
        {status.track && status.track.lyrics && (
          <div
            ref={lyricsRef}
            className="absolute bottom-6 left-1 right-1 text-[#00FF00] bg-black/70 px-2 py-1 text-center whitespace-pre-wrap max-h-24 overflow-y-auto"
            style={{ textShadow: "1px 1px 0 #000" }}
          >
            {lyricLines.map((line, idx) => (
              <div
                key={idx}
                style={{
                  color: idx === activeLineIndex ? "#FFFFFF" : "#00FF00",
                  fontWeight: idx === activeLineIndex ? "bold" : "normal",
                }}
              >
                {line || " "}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default WinampVisualizer;
