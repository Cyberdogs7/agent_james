import React, { useState, useEffect } from "react";
import { Clock } from "lucide-react";

const AppLiveClock = () => {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex items-center gap-1.5 text-[11px] text-gold9/70 font-sans px-2">
      <Clock size={12} className="text-gold9/50" />
      <span>
        {currentTime.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </span>
    </div>
  );
};

export default AppLiveClock;
