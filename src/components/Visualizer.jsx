import React, { useMemo } from 'react';
import { AgentAudioVisualizerAura } from './agents-ui/agent-audio-visualizer-aura';

const Visualizer = ({ audioData, isListening, intensity = 0, width = 600, height = 400 }) => {
    // Determine state
    // 'idle' when not listening/muted.
    // 'speaking' if there's significant audio data.
    // 'listening' if listening but no significant audio data.

    // Average amplitude (0-255)
    const avgAmplitude = audioData.reduce((sum, val) => sum + val, 0) / Math.max(audioData.length, 1);

    // Normalized volume (0-1)
    const volume = avgAmplitude / 255;

    let state = 'idle';
    if (isListening) {
        if (volume > 0.05) {
            state = 'speaking';
        } else {
            state = 'listening';
        }
    }

    return (
        <div
            className="relative flex items-center justify-center"
            style={{ width, height }}
            role="img"
            aria-label={isListening ? "Audio Visualizer - Agent is listening" : "Audio Visualizer - Agent is muted or sleeping"}
        >
            <AgentAudioVisualizerAura
                state={state}
                volume={volume}
                className="w-full h-full"
                color={state === 'idle' ? '#EF4444' : '#1FD5F9'} // Red for idle/muted, Cyan for active
            />
        </div>
    );
};

export default Visualizer;
