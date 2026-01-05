import React from 'react';
import { Mic, MicOff, Settings, Power, Video, VideoOff, Hand, Lightbulb, Printer, Globe, Box } from 'lucide-react';

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

    onToggleHand,
    onToggleKasa,
    showKasaWindow,
    onTogglePrinter,
    showPrinterWindow,
    onToggleCad,
    showCadWindow,
    onToggleBrowser,
    showBrowserWindow,
    activeDragElement,

    position,
    onMouseDown
}) => {
    return (
        <div
            id="tools"
            onMouseDown={onMouseDown}
            className={`absolute px-6 py-3 transition-all duration-200 
                        backdrop-blur-xl bg-black/40 border border-gold9/20 shadow-2xl rounded-full`}
            style={{
                left: position.x,
                top: position.y,
                transform: 'translate(-50%, -50%)',
                pointerEvents: 'auto'
            }}
        >
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay rounded-full"></div>

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

                {/* Hand Tracking Toggle */}
                <button
                    onClick={onToggleHand}
                    title={isHandTrackingEnabled ? "Disable Hand Tracking" : "Enable Hand Tracking"}
                    aria-label={isHandTrackingEnabled ? "Disable Hand Tracking" : "Enable Hand Tracking"}
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${isHandTrackingEnabled
                        ? 'border-orange-500 bg-orange-500/10 text-orange-500 hover:bg-orange-500/20 shadow-[0_0_15px_rgba(249,115,22,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Hand size={24} />
                </button>

                {/* Kasa Light Control */}
                <button
                    onClick={onToggleKasa}
                    title="Toggle Smart Home Controls"
                    aria-label="Toggle Smart Home Controls"
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${showKasaWindow
                        ? 'border-yellow-300 bg-yellow-300/10 text-yellow-300 hover:bg-yellow-300/20 shadow-[0_0_15px_rgba(253,224,71,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Lightbulb size={24} />
                </button>

                {/* 3D Printer Control */}
                <button
                    onClick={onTogglePrinter}
                    title="Toggle 3D Printer Controls"
                    aria-label="Toggle 3D Printer Controls"
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${showPrinterWindow
                        ? 'border-green-400 bg-green-400/10 text-green-400 hover:bg-green-400/20'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Printer size={24} />
                </button>

                {/* CAD Agent Toggle */}
                <button
                    onClick={onToggleCad}
                    title="Toggle CAD Agent"
                    aria-label="Toggle CAD Agent"
                    className={`p-3 rounded-full border-2 transition-all duration-300 ${showCadWindow
                        ? 'border-gold9 bg-gold9/10 text-gold9 hover:bg-gold9/20 shadow-[0_0_15px_rgba(255,215,0,0.3)]'
                        : 'border-gold8 text-gold8 hover:border-gold9 hover:text-gold9'
                        } `}
                >
                    <Box size={24} />
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
            </div>
        </div>
    );
};

export default ToolsModule;
