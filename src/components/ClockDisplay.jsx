import React, { useState, useEffect } from 'react';

const ClockDisplay = () => {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    return (
        <div className="text-right hidden md:block">
            <div className="text-2xl font-bold tracking-widest">
                {time.toLocaleTimeString([], { hour12: false })}
            </div>
            <div className="text-xs text-gold9/60 tracking-[0.2em]">
                {time.toLocaleDateString().toUpperCase()}
            </div>
        </div>
    );
};

export default ClockDisplay;
