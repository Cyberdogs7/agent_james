import React, { useEffect, useRef } from 'react';

const Visualizer = ({ audioData, isListening, intensity = 0, width = 600, height = 400 }) => {
    const canvasRef = useRef(null);
    const audioDataRef = useRef(audioData);

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

            ctx.clearRect(0, 0, w, h);

            // Background fill (transparent)
            ctx.fillStyle = 'transparent';
            ctx.fillRect(0, 0, w, h);

            const radius = Math.min(w, h) / 4; // Base radius of the circle
            const barWidth = 3;
            const numBars = data.length;
            const angleStep = (2 * Math.PI) / numBars;

            // Draw circular spectrum
            for (let i = 0; i < numBars; i++) {
                const value = data[i];
                const barHeight = (value / 255) * (radius * 0.8);

                const angle = i * angleStep;
                const x1 = centerX + radius * Math.cos(angle);
                const y1 = centerY + radius * Math.sin(angle);
                const x2 = centerX + (radius + barHeight) * Math.cos(angle);
                const y2 = centerY + (radius + barHeight) * Math.sin(angle);

                // Add "glitch" effect with chromatic aberration
                // Red channel
                ctx.beginPath();
                ctx.strokeStyle = 'rgba(255, 0, 0, 0.7)';
                ctx.lineWidth = barWidth;
                ctx.moveTo(x1 - 1, y1);
                ctx.lineTo(x2 - 1, y2);
                ctx.stroke();

                // Green channel
                ctx.beginPath();
                ctx.strokeStyle = 'rgba(0, 255, 0, 0.7)';
                ctx.lineWidth = barWidth;
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();

                // Blue channel
                ctx.beginPath();
                ctx.strokeStyle = 'rgba(0, 0, 255, 0.7)';
                ctx.lineWidth = barWidth;
                ctx.moveTo(x1 + 1, y1);
                ctx.lineTo(x2 + 1, y2);
                ctx.stroke();

                // White highlight
                ctx.beginPath();
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.lineWidth = barWidth / 2;
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            }

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
