import React, { useEffect, useState, useRef } from 'react';

const FpsCounter = ({ fpsRef }) => {
    const [fps, setFps] = useState(0);
    const lastFpsRef = useRef(-1);

    useEffect(() => {
        let frameId;
        const updateFps = () => {
            if (fpsRef.current !== undefined && fpsRef.current !== lastFpsRef.current) {
                setFps(fpsRef.current);
                lastFpsRef.current = fpsRef.current;
            }
            frameId = requestAnimationFrame(updateFps);
        };
        frameId = requestAnimationFrame(updateFps);
        return () => cancelAnimationFrame(frameId);
    }, [fpsRef]);

    return (
        <div className="text-[10px] text-green-500 border border-green-900 px-1 rounded ml-2">
            FPS: {fps}
        </div>
    );
};

export default FpsCounter;
