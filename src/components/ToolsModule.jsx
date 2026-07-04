import React from 'react';
import { Mic, MicOff, Settings, Server, Power, Video, VideoOff, Globe, Activity, Music, Pen, Folder, Layout } from 'lucide-react';

const ToolsModule = ({
    isConnected,
    isMuted,
    isVideoOn,
    isHandTrackingEnabled,
    showSettings,
    onTogglePower,
    onToggleMute,
    onToggleVideo,
    onToggleSettings,
    onToggleFleetSettings,

    onToggleMusicPlayer,
    showMusicPlayer,
    onToggleMusicControls,
    showMusicControls,
    onToggleBrowser,
    showBrowserWindow,

    onToggleWritingMode,
    isWritingMode,
    onToggleProjectWindow,
    showProjectWindow,
    onToggleWarRoom,
    showWarRoom,

    activeDragElement,

    position,
    onMouseDown
}) => {
    return (
        <div
            id="tools"
            onMouseDown={onMouseDown}
            className={`absolute px-6 py-3
                         bg-black/80 border border-gold9/20  rounded-full`}
            style={{
                left: position.x,
                top: position.y,
                transform: 'translate(-50%, -50%)',
                pointerEvents: 'auto'
            }}
        >

            <div className="flex justify-center gap-6 relative z-10">
                {/* Power Button */}
                <button
                    onClick={onTogglePower}
                    title={isConnected ? "Disconnect System" : "Connect System"}
                    aria-label={isConnected ? "Disconnect System" : "Connect System"}
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${isConnected
                        ? 'border-green-500 bg-green-500/10 text-green-500 hover:bg-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                        : 'border-gray-600 bg-gray-600/10 text-gray-500 hover:bg-gray-600/20'
                        } `}
                >
                    <Power size={24} />
                </button>

                {/* Mute Button */}
                <button
                    onClick={onToggleMute}
                    disabled={!isConnected}
                    title={isMuted ? "Unmute Microphone" : "Mute Microphone"}
                    aria-label={isMuted ? "Unmute Microphone" : "Mute Microphone"}
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${!isConnected
                        ? 'border-gray-800 text-gray-800 cursor-not-allowed'
                        : isMuted
                            ? 'border-red-500 bg-red-500/10 text-red-500 hover:bg-red-500/20 shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                            : 'border-gold9 bg-gold9/10 text-gold9 hover:bg-gold9/20 shadow-[0_0_15px_rgba(255,215,0,0.3)]'
                        } `}
                >
                    {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
                </button>

                {/* Video Button */}
                <button
                    onClick={onToggleVideo}
                    title={isVideoOn ? "Turn Camera Off" : "Turn Camera On"}
                    aria-label={isVideoOn ? "Turn Camera Off" : "Turn Camera On"}
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${isVideoOn
                        ? 'border-purple-500 bg-purple-500/10 text-purple-500 hover:bg-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    {isVideoOn ? <Video size={24} /> : <VideoOff size={24} />}
                </button>

                {/* Settings Button */}
                <button
                    onClick={onToggleSettings}
                    title="Open Settings"
                    aria-label="Open Settings"
                    className={`p-3 rounded-full border-2 transition-all ${showSettings ? 'border-gold9 text-gold9 bg-gold9/20' : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Settings size={24} />
                </button>

                <button
                    className={`p-2 sm:p-3 rounded-full shadow-[0_0_15px_rgba(255,215,0,0.15)] transition-all pointer-events-auto hover:scale-110 active:scale-95 bg-gray-900 border-gold9/30 hover:bg-gold9/10 text-gold9 border`}
                    onClick={onToggleFleetSettings}
                    title="Fleet Accounts"
                >
                    <Server size={20} className="sm:w-6 sm:h-6" />
                </button>


                {/* Music Player / Visualizer Toggle */}
                <button
                    onClick={onToggleMusicPlayer}
                    title="Toggle Music Visualizer"
                    aria-label="Toggle Music Visualizer"
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${showMusicPlayer
                        ? 'border-pink-500 bg-pink-500/10 text-pink-500 hover:bg-pink-500/20 shadow-[0_0_15px_rgba(236,72,153,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Activity size={24} />
                </button>

                {/* Music Controls Toggle */}
                <button
                    onClick={onToggleMusicControls}
                    title="Toggle Media Controls"
                    aria-label="Toggle Media Controls"
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${showMusicControls
                        ? 'border-cyan-400 bg-cyan-400/10 text-cyan-400 hover:bg-cyan-400/20 shadow-[0_0_15px_rgba(34,211,238,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Music size={24} />
                </button>

                {/* Web Agent Toggle */}
                <button
                    onClick={onToggleBrowser}
                    title="Toggle Web Browser Agent"
                    aria-label="Toggle Web Browser Agent"
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${showBrowserWindow
                        ? 'border-blue-400 bg-blue-400/10 text-blue-400 hover:bg-blue-400/20 shadow-[0_0_15px_rgba(96,165,250,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Globe size={24} />
                </button>

                {/* Project Switching */}
                <button
                    onClick={onToggleProjectWindow}
                    title="Switch Project"
                    aria-label="Switch Project"
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${showProjectWindow
                        ? 'border-indigo-400 bg-indigo-400/10 text-indigo-400 hover:bg-indigo-400/20 shadow-[0_0_15px_rgba(129,140,248,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Folder size={24} />
                </button>

                {/* Writing Mode */}
                <button
                    onClick={onToggleWritingMode}
                    title={isWritingMode ? "Disable Writing Mode" : "Enable Writing Mode"}
                    aria-label={isWritingMode ? "Disable Writing Mode" : "Enable Writing Mode"}
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${isWritingMode
                        ? 'border-pink-500 bg-pink-500/10 text-pink-500 hover:bg-pink-500/20 shadow-[0_0_15px_rgba(236,72,153,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Pen size={24} />
                </button>

                 {/* War Room / Dashboard */}
                 <button
                    onClick={onToggleWarRoom}
                    title="Toggle War Room"
                    aria-label="Toggle War Room"
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${showWarRoom
                        ? 'border-red-600 bg-red-600/10 text-red-600 hover:bg-red-600/20 shadow-[0_0_15px_rgba(220,38,38,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Layout size={24} />
                </button>
            </div>
        </div>
    );
};

export default ToolsModule;
