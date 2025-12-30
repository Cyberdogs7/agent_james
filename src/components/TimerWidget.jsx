import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const TimerWidget = ({ timer, onDismiss }) => {
  const [isDue, setIsDue] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  useEffect(() => {
    // Logic to handle reminder due state
    if (timer.type === 'reminder') {
      const reminderTime = new Date(timer.reminder_time).getTime();
      const now = new Date().getTime();
      if (now >= reminderTime) {
        setIsDue(true);
        const timerId = setTimeout(() => setIsDue(false), 5 * 60 * 1000); // Stop shaking after 5 mins
        return () => clearTimeout(timerId);
      }
    }
  }, [timer]);

  const formatTime = () => {
    if (timer.type === 'timer') {
      const remaining = Math.max(0, Math.round((timer.end_time * 1000 - new Date().getTime()) / 1000));
      if (remaining === 0 && !isFinished) {
        setIsFinished(true);
        setTimeout(() => setIsFinished(false), 5000); // Show "Time's up!" for 5s
      }
      const minutes = Math.floor(remaining / 60);
      const seconds = remaining % 60;
      return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    } else {
      return new Date(timer.reminder_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  };

  const animationClass = isDue ? 'animate-shake' : '';

  if (isFinished) {
      return (
        <div className="bg-green-500/80 text-white p-4 rounded-lg shadow-lg w-full max-w-xs flex flex-col items-center justify-center">
             <h3 className="font-bold text-lg">{timer.name}</h3>
            <p className="text-2xl font-mono">Time's up!</p>
        </div>
      );
  }

  return (
    <div className={`bg-black/60 backdrop-blur-md text-white p-4 rounded-lg shadow-lg w-full max-w-xs flex flex-col ${animationClass}`}>
      <div className="flex justify-between items-start">
        <h3 className="font-bold text-lg mb-2">{timer.name}</h3>
        <button onClick={() => onDismiss(timer.name)} className="text-gray-400 hover:text-white">
          <X size={18} />
        </button>
      </div>
      <p className="text-4xl font-mono text-center">{formatTime()}</p>
    </div>
  );
};

export default TimerWidget;
