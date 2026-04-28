import React, { useState, useEffect } from 'react';
import { Bell, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const NotificationManager = ({ socket }) => {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    if (!socket) return;

    const handleDisplayContent = (data) => {
      if (data.content_type === 'notification') {
        const newNotification = {
          id: Date.now().toString(),
          text: data.data.text,
          duration: data.duration || 10000,
        };

        setNotifications((prev) => [...prev, newNotification]);

        if (newNotification.duration > 0) {
          setTimeout(() => {
            setNotifications((prev) => prev.filter((n) => n.id !== newNotification.id));
          }, newNotification.duration);
        }
      }
    };

    socket.on('display_content', handleDisplayContent);

    return () => {
      socket.off('display_content', handleDisplayContent);
    };
  }, [socket]);

  const removeNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-3 pointer-events-none">
      <AnimatePresence>
        {notifications.map((notification) => (
          <motion.div
            key={notification.id}
            initial={{ opacity: 0, x: 50, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="pointer-events-auto bg-black/80 backdrop-blur-xl border border-white/20 p-4 rounded-xl shadow-2xl w-80 flex items-start gap-3 relative overflow-hidden"
          >
            <div className="mt-1 p-2 bg-blue-500/20 rounded-full shrink-0">
              <Bell className="w-5 h-5 text-blue-400" />
            </div>
            <div className="flex-1 min-w-0 pr-6">
              <h3 className="text-white font-bold text-sm mb-1 tracking-wide">System Notification</h3>
              <p className="text-gray-300 text-sm leading-snug break-words">
                {notification.text}
              </p>
            </div>
            <button
              onClick={() => removeNotification(notification.id)}
              className="absolute top-3 right-3 text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
            {/* Optional Progress Bar for Duration */}
            {notification.duration > 0 && (
                <motion.div
                    initial={{ width: '100%' }}
                    animate={{ width: 0 }}
                    transition={{ duration: notification.duration / 1000, ease: 'linear' }}
                    className="absolute bottom-0 left-0 h-1 bg-blue-500/50"
                />
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default NotificationManager;
