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
            const centerY = h / 2;

            ctx.clearRect(0, 0, w, h);

            // Background fill
            ctx.fillStyle = '#1a1a1a'; // Dark gray
            ctx.fillRect(0, 0, w, h);

            // Grid
            ctx.strokeStyle = 'rgba(255, 215, 0, 0.1)'; // Faint gold
            ctx.lineWidth = 1;

            for (let i = 0; i < w; i += 20) {
                ctx.beginPath();
                ctx.moveTo(i, 0);
                ctx.lineTo(i, h);
                ctx.stroke();
            }

            for (let i = 0; i < h; i += 20) {
                ctx.beginPath();
                ctx.moveTo(0, i);
                ctx.lineTo(w, i);
                ctx.stroke();
            }

            // Oscilloscope line
            ctx.beginPath();
            ctx.strokeStyle = '#ffd700'; // Gold
            ctx.lineWidth = 2;
            ctx.shadowBlur = 10;
            ctx.shadowColor = '#ffd700';

            const sliceWidth = w * 1.0 / data.length;
            let x = 0;

            for (let i = 0; i < data.length; i++) {
                const v = data[i] / 128.0;
                const y = v * h / 2;

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }

                x += sliceWidth;
            }

            ctx.lineTo(canvas.width, canvas.height / 2);
            ctx.stroke();
            ctx.shadowBlur = 0;

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
