import React, { useEffect, useRef } from 'react';

const Visualizer = ({ audioData, isListening, intensity = 0, width = 600, height = 400 }) => {
    const canvasRef = useRef(null);
    const audioDataRef = useRef(audioData);
    const angleRef = useRef(0);

    useEffect(() => {
        audioDataRef.current = audioData;
    }, [audioData]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        let animationId;

        const draw = () => {
            const data = audioDataRef.current;
            const w = canvas.width;
            const h = canvas.height;
            const centerX = w / 2;
            const centerY = h / 2;
            const radius = Math.min(w, h) / 2 - 20;

            // Fading background
            ctx.fillStyle = 'rgba(26, 26, 26, 0.1)'; // Dark gray with low alpha for fading effect
            ctx.fillRect(0, 0, w, h);

            // Sonar grid
            ctx.strokeStyle = 'rgba(255, 215, 0, 0.2)'; // Faint gold
            ctx.lineWidth = 1;
            for (let i = 1; i <= 5; i++) {
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius * (i / 5), 0, 2 * Math.PI);
                ctx.stroke();
            }

            // Rotating sonar sweep
            angleRef.current += 0.02;
            const angle = angleRef.current;

            // Waveform on the sweep
            ctx.beginPath();
            ctx.strokeStyle = '#ffd700'; // Gold
            ctx.lineWidth = 2;
            ctx.shadowBlur = 10;
            ctx.shadowColor = '#ffd700';

            for (let i = 0; i < data.length; i++) {
                const v = data[i] / 128.0; // a value between 0 and 2
                const r = radius + (v - 1) * 30; // Modulate radius by audio data
                const x = centerX + r * Math.cos(angle + (i / data.length) * Math.PI * 0.1); // Spread waveform a bit
                const y = centerY + r * Math.sin(angle + (i / data.length) * Math.PI * 0.1);

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
            ctx.shadowBlur = 0;

            // Sweep line
            const x2 = centerX + radius * Math.cos(angle);
            const y2 = centerY + radius * Math.sin(angle);
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = 'rgba(255, 215, 0, 0.5)';
            ctx.stroke();


            animationId = requestAnimationFrame(draw);
        };

        draw();
        return () => cancelAnimationFrame(animationId);
    }, [width, height]);

    return (
        <div className="relative" style={{ width, height }}>
            <canvas
                ref={canvasRef}
                style={{ width: '100%', height: '100%' }}
            />
        </div>
    );
};

export default Visualizer;
