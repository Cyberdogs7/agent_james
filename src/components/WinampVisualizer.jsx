import React, { useEffect, useRef, useState } from 'react';
import { X, Minimize, Maximize, Play, Pause, Square, SkipForward, SkipBack, Volume2 } from 'lucide-react';

const WinampVisualizer = ({ socket, onClose }) => {
    const canvasRef = useRef(null);
    const [visData, setVisData] = useState(new Array(64).fill(0));
    const [status, setStatus] = useState({ status: 'stopped', track: null });
    const [mode, setMode] = useState('spectrum'); // 'spectrum' or 'oscilloscope'
    const animationRef = useRef(null);
    const dataRef = useRef(new Array(64).fill(0));

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

        socket.on('music_vis_data', onVisData);
        socket.on('music_status', onStatus);

        return () => {
            socket.off('music_vis_data', onVisData);
            socket.off('music_status', onStatus);
        };
    }, [socket]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        const draw = () => {
            const w = canvas.width;
            const h = canvas.height;
            const data = dataRef.current;

            ctx.fillStyle = '#000000';
            ctx.fillRect(0, 0, w, h);

            if (mode === 'spectrum') {
                const barWidth = w / data.length;

                for (let i = 0; i < data.length; i++) {
                    const value = data[i];
                    const percent = value / 255;
                    const barHeight = percent * h;

                    // Winamp Colors: Green -> Yellow -> Red
                    // Simple gradient approximation
                    let color = '#00FF00'; // Green
                    if (percent > 0.5) color = '#FFFF00'; // Yellow
                    if (percent > 0.8) color = '#FF0000'; // Red

                    ctx.fillStyle = color;
                    ctx.fillRect(i * barWidth, h - barHeight, barWidth - 1, barHeight);

                    // Peak (simple white dot)
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillRect(i * barWidth, h - barHeight - 2, barWidth - 1, 1);
                }
            } else {
                // Oscilloscope
                ctx.beginPath();
                ctx.strokeStyle = '#00FF00';
                ctx.lineWidth = 2;

                const sliceWidth = w * 1.0 / data.length;
                let x = 0;

                for(let i = 0; i < data.length; i++) {
                    const v = data[i] / 128.0; // 0-255 -> 0-2 roughly
                    const y = v * h/2;

                    if(i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);

                    x += sliceWidth;
                }
                ctx.stroke();
            }

            animationRef.current = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            if (animationRef.current) cancelAnimationFrame(animationRef.current);
        };
    }, [mode]);

    const handleControl = (action) => {
        socket.emit('control_music', { action });
    };

    return (
        <div className="flex flex-col h-full bg-[#1a1a1a] text-[#00FF00] font-mono text-xs select-none">
            {/* Header / Title Bar */}
            <div className="h-5 bg-[#2d2d2d] flex items-center justify-between px-2 cursor-grab active:cursor-grabbing border-b border-[#4a4a4a]">
                <div className="flex items-center gap-1">
                    <span className="text-[#cbced0]">WINAMP</span>
                    <span className="text-[#00FF00] animate-pulse">⚡</span>
                </div>
                <div className="flex gap-1">
                    <button onClick={() => setMode(m => m === 'spectrum' ? 'oscilloscope' : 'spectrum')} className="hover:text-white" title="Toggle Mode" aria-label="Toggle Mode">M</button>
                    <button onClick={onClose} className="hover:text-white" title="Close" aria-label="Close"><X size={10} /></button>
                </div>
            </div>

            {/* Main Display */}
            <div className="flex-1 relative border border-[#4a4a4a] m-1 bg-black">
                <canvas
                    ref={canvasRef}
                    width={300}
                    height={150}
                    className="w-full h-full"
                    onClick={() => setMode(m => m === 'spectrum' ? 'oscilloscope' : 'spectrum')}
                />

                {/* Track Info Overlay */}
                <div className="absolute top-1 left-1 text-[#00FF00] bg-black/50 px-1">
                    {status.track ? `${status.track.title} (${status.status})` : "No Track Loaded"}
                </div>

                {/* Bitrate / Time placeholder */}
                <div className="absolute bottom-1 right-1 text-[#00FF00] bg-black/50 px-1">
                    {status.status === 'playing' ? "128 kbps" : ""}
                </div>
            </div>

            {/* Controls */}
            <div className="h-12 flex items-center justify-between px-2 pb-1">
                <div className="flex items-center gap-2">
                    <button onClick={() => handleControl('stop')} className="p-1 hover:bg-[#333] border border-[#4a4a4a] rounded-sm" title="Stop" aria-label="Stop"><Square size={10} fill="#00FF00" /></button>
                    <button onClick={() => handleControl('play')} className="p-1 hover:bg-[#333] border border-[#4a4a4a] rounded-sm" title="Play" aria-label="Play"><Play size={10} fill="#00FF00" /></button>
                    <button onClick={() => handleControl('pause')} className="p-1 hover:bg-[#333] border border-[#4a4a4a] rounded-sm" title="Pause" aria-label="Pause"><Pause size={10} fill="#00FF00" /></button>
                    <button onClick={() => handleControl('stop')} className="p-1 hover:bg-[#333] border border-[#4a4a4a] rounded-sm" title="Previous Track" aria-label="Previous Track"><SkipBack size={10} fill="#00FF00" /></button>
                    <button onClick={() => handleControl('stop')} className="p-1 hover:bg-[#333] border border-[#4a4a4a] rounded-sm" title="Next Track" aria-label="Next Track"><SkipForward size={10} fill="#00FF00" /></button>
                </div>

                <div className="flex items-center gap-1">
                    <button onClick={() => handleControl('volume_down')} className="p-1 hover:bg-[#333]" title="Volume Down" aria-label="Volume Down">-</button>
                    <Volume2 size={12} />
                    <button onClick={() => handleControl('volume_up')} className="p-1 hover:bg-[#333]" title="Volume Up" aria-label="Volume Up">+</button>
                </div>
            </div>
        </div>
    );
};

export default WinampVisualizer;
