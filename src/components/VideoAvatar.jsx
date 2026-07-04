import React, { useState, memo, useEffect, useRef } from 'react';

const ASSETS = {
  static: '/Base/static_image.png',
  idle: '/Base/idle.mp4',
  thinking: '/Base/thinking.mp4',
  intense_thinking: '/Base/intense_thinking.mp4',
  delegate_task: '/Base/delegate_task.mp4',
  success: '/Base/success.mp4',
  alert: '/Base/alert.mp4',
};



const VideoAvatar = memo(({ reaction = 'idle', width = 600, height = 400 }) => {
  const [hasError, setHasError] = useState(false);
  const videoSrc = ASSETS[reaction] || ASSETS.idle;


  const videoRef = useRef(null);

  useEffect(() => {
      setHasError(false);
      if (videoRef.current) {
          videoRef.current.src = videoSrc;
          videoRef.current.load();
          const playPromise = videoRef.current.play();
          if (playPromise !== undefined) {
              playPromise.catch(e => {
                  console.warn("Autoplay prevented:", e);
              });
          }
      }
  }, [videoSrc]);

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
});

VideoAvatar.displayName = 'VideoAvatar';

export default VideoAvatar;
