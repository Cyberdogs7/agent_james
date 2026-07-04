import httpx
import traceback
import os
import urllib.parse

class WeatherAgent:
    def __init__(self):
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    def _wwo_to_wmo(self, wwo_code):
        try:
            wwo_code = int(wwo_code)
        except (ValueError, TypeError):
            return 0
            
        mapping = {
            113: 0, 116: 2, 119: 3, 122: 3, 143: 45, 176: 80, 179: 85, 182: 85,
            185: 56, 200: 95, 227: 71, 230: 71, 248: 45, 260: 48, 263: 51,
            266: 53, 281: 56, 284: 57, 293: 61, 296: 61, 299: 63, 302: 63,
            305: 65, 308: 65, 311: 66, 314: 67, 317: 71, 320: 73, 323: 71,
            326: 71, 329: 73, 332: 73, 335: 75, 338: 75, 350: 77, 353: 80,
            356: 81, 359: 82, 362: 85, 365: 85, 368: 85, 371: 86, 374: 77,
            377: 77, 386: 95, 389: 96, 392: 95, 395: 99
        }
        return mapping.get(wwo_code, 0)

    async def get_weather(self, location, forecast_days=7, past_days=0, hourly=None, daily=None):
        if self.include_raw:
            print(f"[WeatherAgent] Getting weather for: '{location}'")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                encoded_location = urllib.parse.quote(location)
                url = f"https://wttr.in/{encoded_location}?format=j1"
                
                if self.include_raw:
                    print(f"[WeatherAgent] Requesting wttr.in URL: {url}")
                
                response = await client.get(url)
                response.raise_for_status()
                weather_data = response.json()
                
                forecast = []
                for day in weather_data.get('weather', []):
                    date = day.get('date')
                    temp_max = float(day.get('maxtempC', 0))
                    temp_min = float(day.get('mintempC', 0))
                    
                    hourly_data = day.get('hourly', [])
                    weather_code = 0
                    precipitation = 0.0
                    
                    if hourly_data:
                        noon_hour = hourly_data[len(hourly_data)//2]
                        wwo_code = noon_hour.get('weatherCode', 0)
                        weather_code = self._wwo_to_wmo(wwo_code)
                        
                        # Sum up precipitation for the day
                        precipitation = sum(float(h.get('precipMM', 0)) for h in hourly_data)
                        
                    forecast.append({
                        "date": date,
                        "weather_code": weather_code,
                        "temp_max": temp_max,
                        "temp_min": temp_min,
                        "precipitation": precipitation
                    })
                    
                if not forecast:
                    return f"Could not find weather data for: {location}"
                    
                return forecast
                
        except httpx.HTTPStatusError as e:
            if self.include_raw:
                print(f"[WeatherAgent] [ERR] HTTP error: {e}")
            return f"Error processing weather request: {e.response.status_code}"
        except Exception as e:
            if self.include_raw:
                print(f"[WeatherAgent] [ERR] Failed to get weather: {e}")
                traceback.print_exc()
            return "Failed to get weather data."
