import React from 'react';
import { Sun, Cloud, CloudRain, CloudSnow, Wind, CloudFog, CloudLightning, CloudDrizzle } from 'lucide-react';

const WeatherWidget = ({ data }) => {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return null;
  }

  const getWeatherIcon = (code) => {
    switch (code) {
      case 0:
      case 1:
        return <Sun size={32} className="text-yellow-400" />;
      case 2:
        return <Cloud size={32} className="text-gray-400" />;
      case 3:
        return <Cloud size={32} className="text-gray-400" />;
      case 45:
      case 48:
        return <CloudFog size={32} className="text-gray-500" />;
      case 51:
      case 53:
      case 55:
        return <CloudDrizzle size={32} className="text-blue-400" />;
      case 56:
      case 57:
        return <CloudDrizzle size={32} className="text-blue-400" />; // Freezing Drizzle
      case 61:
      case 63:
      case 65:
        return <CloudRain size={32} className="text-blue-400" />;
      case 66:
      case 67:
        return <CloudRain size={32} className="text-blue-400" />; // Freezing Rain
      case 71:
      case 73:
      case 75:
        return <CloudSnow size={32} className="text-white" />;
      case 77:
        return <CloudSnow size={32} className="text-white" />; // Snow grains
      case 80:
      case 81:
      case 82:
        return <CloudRain size={32} className="text-blue-400" />; // Rain showers
      case 85:
      case 86:
        return <CloudSnow size={32} className="text-white" />; // Snow showers
      case 95:
      case 96:
      case 99:
        return <CloudLightning size={32} className="text-yellow-500" />;
      default:
        return <Wind size={32} className="text-gray-500" />;
    }
  };

  const getDayOfWeek = (dateString) => {
    const date = new Date(dateString);
    // Add time zone offset to prevent day shifting
    const adjustedDate = new Date(date.getTime() + date.getTimezoneOffset() * 60000);
    return adjustedDate.toLocaleDateString('en-US', { weekday: 'short' });
  };


  return (
    <div className="bg-black/50 backdrop-blur-md text-white p-4 rounded-lg shadow-lg w-full max-w-2xl">
      <div className="flex justify-between space-x-2">
        {data.slice(0, 7).map((day, index) => (
          <div key={index} className="flex flex-col items-center p-2 rounded-lg flex-1">
            <p className="font-bold text-sm">{getDayOfWeek(day.date)}</p>
            <div className="my-1">{getWeatherIcon(day.weather_code)}</div>
            <p className="text-sm">
              {Math.round(day.temp_max)}° / {Math.round(day.temp_min)}°
            </p>
             <p className="text-xs text-gray-400 mt-1">{day.precipitation.toFixed(1)}mm</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WeatherWidget;
