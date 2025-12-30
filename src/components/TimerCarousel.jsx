import React, { useState, useEffect } from 'react';
import TimerWidget from './TimerWidget';

const TimerCarousel = ({ timers, onDismiss }) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (timers.length > 1) {
      const intervalId = setInterval(() => {
        setCurrentIndex((prevIndex) => (prevIndex + 1) % timers.length);
      }, 5000); // Flip every 5 seconds

      return () => clearInterval(intervalId);
    }
  }, [timers]);

  if (!timers || timers.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center justify-center w-full h-full">
      <TimerWidget
        key={timers[currentIndex].name}
        timer={timers[currentIndex]}
        onDismiss={onDismiss}
      />
    </div>
  );
};

export default TimerCarousel;
