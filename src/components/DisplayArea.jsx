import React, { useState, useEffect, useRef } from 'react';
import Visualizer from './Visualizer';
import WeatherWidget from './WeatherWidget';
import TimerCarousel from './TimerCarousel';
import AvatarCanvas from './AvatarCanvas';
import SelectWindow from './SelectWindow';
import { X } from 'lucide-react';

const DisplayArea = ({ socket, isListening, timers, currentProject, facePosition }) => {
  const [displayContent, setDisplayContent] = useState(null);
  const [isVisible, setIsVisible] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState(null);
  const timerRef = useRef(null);

  const [aiAudioData, setAiAudioData] = useState(new Array(64).fill(0));
  const audioHistoryRef = useRef([]);

  useEffect(() => {
        if (!socket) return;
        const handleAudio = (data) => {
            let rawData;
            if (data.data instanceof ArrayBuffer) {
                const int16View = new Int16Array(data.data);
                rawData = new Array(Math.min(int16View.length, 64)); // The visualizer uses a 64-element array typically
                const step = Math.max(1, Math.floor(int16View.length / rawData.length));
                for (let i = 0; i < rawData.length; i++) {
                    // Take max absolute value in the window
                    let maxVal = 0;
                    for (let j = 0; j < step && (i * step + j) < int16View.length; j++) {
                        maxVal = Math.max(maxVal, Math.abs(int16View[i * step + j]));
                    }
                    // Scale 0-32768 to 0-255
                    rawData[i] = Math.min(255, Math.floor((maxVal / 32768) * 255));
                }
            } else if (Array.isArray(data.data)) {
                // Fallback if it's still an array for some reason
                rawData = data.data.slice(0, 64);
            } else {
                return;
            }

            const history = audioHistoryRef.current;
            history.push(rawData);
            if (history.length > 5) {
                history.shift();
            }

            if (history.length > 0) {
                const smoothedData = new Array(rawData.length).fill(0);
                for (let i = 0; i < rawData.length; i++) {
                    let sum = 0;
                    for (let j = 0; j < history.length; j++) {
                        sum += history[j][i] || 0;
                    }
                    smoothedData[i] = sum / history.length;
                }

                const silenceThreshold = 5;
                const isSilent = smoothedData.every(val => val < silenceThreshold);
                if (isSilent) {
                    setAiAudioData(new Array(rawData.length).fill(0));
                } else {
                    setAiAudioData(smoothedData);
                }
            } else {
                setAiAudioData(rawData);
            }
        };

        socket.on('audio_data', handleAudio);
        return () => socket.off('audio_data', handleAudio);
  }, [socket]);

  const intensity = aiAudioData.length > 0 ? aiAudioData.reduce((a, b) => a + b, 0) / aiAudioData.length / 255 : 0;

  // Check for project-specific avatar
  useEffect(() => {
      if (currentProject) {
          const port = import.meta.env.SERVER_PORT || 8180;
          const hostname = window.location.hostname;
          const url = `http://${hostname}:${port}/projects/${currentProject}/avatar.vrm`;

          fetch(url, { method: 'HEAD' })
              .then(res => {
                  if (res.ok) {
                      console.log("[DisplayArea] Found custom avatar:", url);
                      setAvatarUrl(url);
                  } else {
                      setAvatarUrl(null);
                  }
              })
              .catch(() => setAvatarUrl(null));
      }
  }, [currentProject]);

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
      // Render Avatar if available
      if (avatarUrl) {
          return <AvatarCanvas audioData={aiAudioData} vrmUrl={avatarUrl} facePosition={facePosition} />;
      }
      return <Visualizer isListening={isListening} audioData={aiAudioData} intensity={intensity} />;
    }

    switch (displayContent.content_type) {
      case 'image':
        return <img src={displayContent.url} alt="Displayed content" className="max-h-full max-w-full object-contain" />;
      case 'widget':
        if (displayContent.widget_type === 'weather') {
          return <WeatherWidget data={displayContent.data} />;
        }
        if (displayContent.widget_type === 'select') {
          return <SelectWindow options={displayContent.data.options} socket={socket} onSelect={handleDismiss} />;
        }
        return null;
      default:
        return <Visualizer isListening={isListening} audioData={aiAudioData} intensity={intensity} />;
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
              className="absolute top-2 right-2 p-1.5 bg-black/80 hover:bg-black/80 rounded-full text-white transition-colors z-10"
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
