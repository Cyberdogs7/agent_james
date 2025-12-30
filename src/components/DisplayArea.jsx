import React, { useState, useEffect, useRef } from 'react';
import Visualizer from './Visualizer';
import WeatherWidget from './WeatherWidget';
import TimerCarousel from './TimerCarousel';
import { X } from 'lucide-react';

const DisplayArea = ({ socket, isListening, audioData, intensity, timers }) => {
  const [displayContent, setDisplayContent] = useState(null);
  const [isVisible, setIsVisible] = useState(false);
  const timerRef = useRef(null);

  const handleTimerDismiss = (name) => {
    if (socket) {
      socket.emit('delete_timer', { name });
    }
  };

  const handleDisplay = (data) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    if (data.content_type === 'clear') {
      handleDismiss();
      return;
    }

    setDisplayContent(data);
    setIsVisible(true);

    const duration = data.duration || (data.content_type === 'image' ? 10000 : 120000); // 10s for images, 2min for widgets

    timerRef.current = setTimeout(() => {
      handleDismiss();
    }, duration);
  };

  const handleDismiss = () => {
    setIsVisible(false);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    // Allow for fade-out transition
    setTimeout(() => {
      setDisplayContent(null);
    }, 300);
  };

  useEffect(() => {
    if (socket) {
      socket.on('display_content', handleDisplay);
    }
    return () => {
      if (socket) {
        socket.off('display_content', handleDisplay);
      }
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [socket]);

  const renderContent = () => {
    if (!displayContent) {
      if (timers && timers.length > 0) {
        return <TimerCarousel timers={timers} onDismiss={handleTimerDismiss} />;
      }
      return <Visualizer isListening={isListening} audioData={audioData} intensity={intensity} />;
    }

    switch (displayContent.content_type) {
      case 'image':
        return <img src={displayContent.url} alt="Displayed content" className="max-h-full max-w-full object-contain" />;
      case 'widget':
        if (displayContent.widget_type === 'weather') {
          return <WeatherWidget data={displayContent.data} />;
        }
        return null;
      default:
        return <Visualizer isListening={isListening} audioData={audioData} intensity={intensity} />;
    }
  };

  const isDefaultVisualizer = !displayContent;

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {isDefaultVisualizer && renderContent()}

      <div
        className={`absolute inset-0 w-full h-full transition-opacity duration-300 flex items-center justify-center ${
          isVisible && !isDefaultVisualizer ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        {!isDefaultVisualizer && (
          <>
            {renderContent()}
            <button
              onClick={handleDismiss}
              className="absolute top-2 right-2 p-1.5 bg-black/50 hover:bg-black/80 rounded-full text-white transition-colors z-10"
            >
              <X size={18} />
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default DisplayArea;
