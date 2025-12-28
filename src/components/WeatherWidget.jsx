import React from 'react';
import { Sun, Cloud, CloudRain, CloudSnow, Wind } from 'lucide-react';

const WeatherWidget = ({ data }) => {
  if (!data) {
    return null;
  }

  const { temperature, condition, location } = data;

  const getWeatherIcon = (condition) => {
    if (condition.toLowerCase().includes('sun') || condition.toLowerCase().includes('clear')) {
      return <Sun size={48} className="text-yellow-400" />;
    }
    if (condition.toLowerCase().includes('cloud')) {
      return <Cloud size={48} className="text-gray-400" />;
    }
    if (condition.toLowerCase().includes('rain')) {
      return <CloudRain size={48} className="text-blue-400" />;
    }
    if (condition.toLowerCase().includes('snow')) {
      return <CloudSnow size={48} className="text-white" />;
    }
    return <Wind size={48} className="text-gray-500" />;
  };

  return (
    <div className="bg-black/50 backdrop-blur-md text-white p-6 rounded-lg shadow-lg w-80 h-48 flex flex-col justify-between">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-bold">{location || 'Weather'}</h2>
          <p className="text-4xl font-bold">{temperature}°</p>
        </div>
        <div>{getWeatherIcon(condition)}</div>
      </div>
      <div className="text-lg">{condition}</div>
    </div>
  );
};

export default WeatherWidget;
