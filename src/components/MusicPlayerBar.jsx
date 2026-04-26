import React, { useEffect, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, Shuffle, Repeat, ChevronDown, ChevronUp } from 'lucide-react';

const MusicPlayerBar = ({ socket }) => {
    const [status, setStatus] = useState({ status: 'stopped', track: null });
    const [isVisible, setIsVisible] = useState(false);
    const [isMinimized, setIsMinimized] = useState(false);

    useEffect(() => {
        if (!socket) return;

        const onStatus = (payload) => {
            console.log("[MusicPlayerBar] Status:", payload);
            setStatus(payload);
            if (payload.status === 'playing' || payload.status === 'paused' || payload.track) {
                setIsVisible(true);
            }
            if (payload.status === 'stopped' && !payload.track) {
                setIsVisible(false);
            }
        };

        socket.on('music_status', onStatus);

        return () => {
            socket.off('music_status', onStatus);
        };
    }, [socket]);

    const handleControl = (action) => {
        socket.emit('control_music', { action });
    };

    const formatTime = (seconds) => {
        if (!seconds || isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    if (!isVisible) return null;

    const progress = status.track?.progress || 0;
    const duration = status.track?.duration || 0;
    const progressPercent = duration > 0 ? (progress / duration) * 100 : 0;

    if (isMinimized) {
        return (
            <div className="fixed bottom-4 right-4 z-[100]">
                <button
                    onClick={() => setIsMinimized(false)}
                    className="w-12 h-12 bg-[#212121] border border-[#383838] rounded-full flex items-center justify-center text-white hover:scale-105 transition-transform shadow-lg focus-visible:ring-2 focus-visible:ring-white outline-none"
                    title="Show Music Player"
                    aria-label="Show Music Player"
                >
                    <ChevronUp size={24} />
                </button>
            </div>
        );
    }

    return (
        <div className="fixed bottom-0 left-0 right-0 h-[72px] bg-[#212121] border-t border-[#383838] flex items-center px-4 z-[100] text-white select-none">
            {/* Left: Track Info */}
            <div className="flex items-center w-1/3 gap-4">
                <div className="w-12 h-12 bg-[#383838] rounded flex items-center justify-center shrink-0">
                    <span className="text-xl">🎵</span>
                </div>
                <div className="flex flex-col overflow-hidden">
                    <span className="font-bold text-[14px] truncate" title={status.track?.title}>
                        {status.track?.title || 'Unknown Title'}
                    </span>
                    <span className="text-[#aaaaaa] text-[12px] truncate" title={status.track?.artist}>
                        {status.track?.artist || 'Unknown Artist'}
                    </span>
                </div>
            </div>

            {/* Center: Controls */}
            <div className="flex-1 flex flex-col items-center justify-center gap-1">
                <div className="flex items-center gap-6">
                    <button
                        className="text-[#aaaaaa] hover:text-white transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-white outline-none rounded"
                        disabled
                        title="Shuffle (coming soon)"
                        aria-label="Shuffle"
                    >
                        <Shuffle size={18} />
                    </button>
                    <button
                        onClick={() => handleControl('previous')}
                        className="text-[#aaaaaa] hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-white outline-none rounded"
                        title="Previous Track"
                        aria-label="Previous Track"
                    >
                        <SkipBack size={20} fill="currentColor" />
                    </button>
                    <button
                        onClick={() => handleControl(status.status === 'playing' ? 'pause' : 'resume')}
                        className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-black hover:scale-105 transition-transform focus-visible:ring-2 focus-visible:ring-white outline-none"
                        title={status.status === 'playing' ? 'Pause' : 'Play'}
                        aria-label={status.status === 'playing' ? 'Pause' : 'Play'}
                    >
                        {status.status === 'playing' ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-1" />}
                    </button>
                    <button
                        onClick={() => handleControl('next')}
                        className="text-[#aaaaaa] hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-white outline-none rounded"
                        title="Next Track"
                        aria-label="Next Track"
                    >
                        <SkipForward size={20} fill="currentColor" />
                    </button>
                    <button
                        className="text-[#aaaaaa] hover:text-white transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-white outline-none rounded"
                        disabled
                        title="Repeat (coming soon)"
                        aria-label="Repeat"
                    >
                        <Repeat size={18} />
                    </button>
                </div>
                {/* Progress bar */}
                <div className="w-full max-w-md flex items-center gap-2 text-[11px] text-[#aaaaaa]">
                    <span>{formatTime(progress)}</span>
                    <div className="flex-1 h-1 bg-[#4d4d4d] rounded-full overflow-hidden cursor-pointer hover:h-1.5 transition-all">
                        <div
                            className="h-full bg-red-600 rounded-full relative"
                            style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
                        >
                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-red-600 rounded-full opacity-0 hover:opacity-100 transition-opacity"></div>
                        </div>
                    </div>
                    <span>{status.track?.time || '0:00'}</span>
                </div>
            </div>

            {/* Right: Additional Controls */}
            <div className="w-1/3 flex items-center justify-end gap-4">
                <div className="flex items-center gap-2 text-[#aaaaaa] group">
                    <button
                        onClick={() => handleControl('volume_down')}
                        className="hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-white outline-none rounded"
                        title="Volume Down"
                        aria-label="Volume Down"
                    >
                        <Volume2 size={20} />
                    </button>
                    <div className="w-24 h-1 bg-[#4d4d4d] rounded-full overflow-hidden cursor-pointer hover:h-1.5 transition-all group-hover:bg-[#5a5a5a]" title="Volume" aria-label="Volume Control" role="slider" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50">
                        <div className="w-1/2 h-full bg-white rounded-full"></div>
                    </div>
                </div>
                <button
                    onClick={() => setIsMinimized(true)}
                    className="text-[#aaaaaa] hover:text-white transition-colors ml-4 focus-visible:ring-2 focus-visible:ring-white outline-none rounded"
                    title="Hide Controls"
                    aria-label="Hide Controls"
                >
                    <ChevronDown size={20} />
                </button>
            </div>
        </div>
    );
};

export default MusicPlayerBar;
