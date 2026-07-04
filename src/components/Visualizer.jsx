import React, { useMemo } from 'react';
import { AgentAudioVisualizerAura } from './agents-ui/agent-audio-visualizer-aura';
import { AgentAudioVisualizerButterchurn } from './agents-ui/agent-audio-visualizer-butterchurn';

const Visualizer = ({
    audioDataRef,
    isListening,
    intensity = 0,
    width = 600,
    height = 400,
    mode: initialMode = 'aura', // 'aura' | 'butterchurn'
    preset,
}) => {
    const [volume, setVolume] = React.useState(0);
    const [state, setState] = React.useState('idle');
    const [currentMode, setCurrentMode] = React.useState(initialMode);

    React.useEffect(() => {
        let animationFrameId;

        const updateVisualizer = () => {
            const audioData = audioDataRef?.current || [];
            const avgAmplitude = audioData.reduce((sum, val) => sum + val, 0) / Math.max(audioData.length, 1);
            const currentVolume = avgAmplitude / 255;
            setVolume(currentVolume);

            if (isListening) {
                if (currentVolume > 0.05) {
                    setState('speaking');
                } else {
                    setState('listening');
                }
            } else {
                setState('idle');
            }

            animationFrameId = requestAnimationFrame(updateVisualizer);
        };

        updateVisualizer();

        return () => cancelAnimationFrame(animationFrameId);
    }, [audioDataRef, isListening]);

    return (
        <div
            className="relative flex items-center justify-center cursor-pointer group"
            style={{ width, height }}
            role="img"
            aria-label={isListening ? "Audio Visualizer - Agent is listening" : "Audio Visualizer - Agent is muted or sleeping"}
        >
            <button
                onClick={(e) => { e.stopPropagation(); setCurrentMode(m => m === 'aura' ? 'butterchurn' : 'aura'); }}
                className="absolute top-2 right-2 z-10 bg-black/50 text-white px-2 py-1 rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80"
            >
                Mode: {currentMode === 'aura' ? 'Aura' : 'Milkshake'}
            </button>
            {currentMode === 'butterchurn' ? (
                <AgentAudioVisualizerButterchurn
                    state={state}
                    volume={volume}
                    preset={preset}
                    className="w-full h-full"
                />
            ) : (
                <AgentAudioVisualizerAura
                    state={state}
                    volume={volume}
                    className="w-full h-full"
                    color={state === 'idle' ? '#EF4444' : '#1FD5F9'} // Red for idle/muted, Cyan for active
                />
            )}
        </div>
    );
};

export default Visualizer;
