import React, { useEffect, useRef, useState } from 'react';

const ASSETS = {
  static: '/base/static_image.png',
  idle: '/base/idle.mp4',
  thinking: '/base/thinking.mp4',
  intense_thinking: '/base/intense_thinking.mp4',
  delegate_task: '/base/delegate_task.mp4',
  success: '/base/success.mp4',
  alert: '/base/alert.mp4',
};

const VideoAvatar = ({ reaction = 'idle', width = 600, height = 400 }) => {
  const videoRef = useRef(null);
  const [videoSrc, setVideoSrc] = useState(ASSETS.idle);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    // Map reaction state to appropriate asset
    let targetSrc = ASSETS[reaction];
    if (!targetSrc) {
        targetSrc = ASSETS.idle; // fallback to idle if reaction is unknown
    }

    if (videoSrc !== targetSrc) {
        setVideoSrc(targetSrc);
        setHasError(false); // Reset error state on source change
    }
  }, [reaction, videoSrc]);

  useEffect(() => {
      // When source changes, ensure video plays
      if (videoRef.current && !hasError) {
          videoRef.current.load();
          const playPromise = videoRef.current.play();
          if (playPromise !== undefined) {
              playPromise.catch((e) => {
                  console.error("Auto-play failed for reaction video:", e);
              });
          }
      }
  }, [videoSrc, hasError]);

  const handleError = () => {
      console.warn("Failed to load video, falling back to static image:", videoSrc);
      setHasError(true);
  };

  return (
    <div
      className="relative flex items-center justify-center overflow-hidden"
      style={{ width: '100%', height: '100%', minWidth: width, minHeight: height }}
    >
      {hasError ? (
          <img 
            src={ASSETS.static} 
            alt="Persona Static" 
            className="w-full h-full object-contain" 
          />
      ) : (
          <video
            ref={videoRef}
            src={videoSrc}
            autoPlay
            loop
            muted
            playsInline
            onError={handleError}
            className="w-full h-full object-contain"
          />
      )}
    </div>
  );
};

export default VideoAvatar;
