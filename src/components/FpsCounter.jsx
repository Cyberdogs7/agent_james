import React, { useEffect, useRef } from 'react';

const FpsCounter = ({ fpsRef }) => {
    const displayRef = useRef(null);

    useEffect(() => {
        let frameId;
        const updateFps = () => {
            if (displayRef.current && fpsRef.current !== undefined) {
                displayRef.current.innerText = `FPS: ${fpsRef.current}`;
            }
            frameId = requestAnimationFrame(updateFps);
        };
        frameId = requestAnimationFrame(updateFps);
        return () => cancelAnimationFrame(frameId);
    }, [fpsRef]);

    return (
        <div ref={displayRef} className="text-[10px] text-green-500 border border-green-900 px-1 rounded ml-2">
            FPS: 0
        </div>
    );
};

export default FpsCounter;
