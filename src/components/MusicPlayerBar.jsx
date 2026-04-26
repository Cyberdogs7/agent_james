import React, { useEffect, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, Shuffle, Repeat } from 'lucide-react';

const MusicPlayerBar = ({ socket }) => {
    const [status, setStatus] = useState({ status: 'stopped', track: null });
    const [isVisible, setIsVisible] = useState(false);

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

    if (!isVisible) return null;

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
                    <button className="text-[#aaaaaa] hover:text-white transition-colors disabled:opacity-50" disabled>
                        <Shuffle size={18} />
                    </button>
                    <button onClick={() => handleControl('previous')} className="text-[#aaaaaa] hover:text-white transition-colors">
                        <SkipBack size={20} fill="currentColor" />
                    </button>
                    <button
                        onClick={() => handleControl(status.status === 'playing' ? 'pause' : 'resume')}
                        className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-black hover:scale-105 transition-transform"
                    >
                        {status.status === 'playing' ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-1" />}
                    </button>
                    <button onClick={() => handleControl('next')} className="text-[#aaaaaa] hover:text-white transition-colors">
                        <SkipForward size={20} fill="currentColor" />
                    </button>
                    <button className="text-[#aaaaaa] hover:text-white transition-colors disabled:opacity-50" disabled>
                        <Repeat size={18} />
                    </button>
                </div>
                {/* Progress bar placeholder (simulated) */}
                <div className="w-full max-w-md flex items-center gap-2 text-[11px] text-[#aaaaaa]">
                    <span>0:00</span>
                    <div className="flex-1 h-1 bg-[#4d4d4d] rounded-full overflow-hidden cursor-pointer hover:h-1.5 transition-all">
                        <div className="w-1/3 h-full bg-red-600 rounded-full relative">
                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-red-600 rounded-full opacity-0 hover:opacity-100 transition-opacity"></div>
                        </div>
                    </div>
                    <span>{status.track?.time || '0:00'}</span>
                </div>
            </div>

            {/* Right: Additional Controls */}
            <div className="w-1/3 flex items-center justify-end gap-4">
                <div className="flex items-center gap-2 text-[#aaaaaa] group">
                    <button onClick={() => handleControl('volume_down')} className="hover:text-white transition-colors">
                        <Volume2 size={20} />
                    </button>
                    <div className="w-24 h-1 bg-[#4d4d4d] rounded-full overflow-hidden cursor-pointer hover:h-1.5 transition-all group-hover:bg-[#5a5a5a]">
                        <div className="w-1/2 h-full bg-white rounded-full"></div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MusicPlayerBar;
