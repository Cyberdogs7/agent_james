import httpx
import traceback
import os

INCLUDE_RAW_LOGS = os.getenv("INCLUDE_RAW_LOGS", "True").lower() == "true"

get_weather_tool = {
    "name": "get_weather",
    "description": "Fetches weather forecast data for a given location. Can retrieve future forecasts (up to 16 days), historical data (up to 92 days), and specific hourly or daily weather variables (e.g., temperature_2m_max, wind_speed_10m, uv_index). Always use this tool when the user asks for the weather.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "location": {
                "type": "STRING",
                "description": "The city and state, e.g., San Francisco, CA"
            },
            "forecast_days": {
                "type": "INTEGER",
                "description": "The number of days to forecast (0-16). Defaults to 7."
            },
            "past_days": {
                "type": "INTEGER",
                "description": "The number of past days to retrieve data for (0-92)."
            },
            "hourly": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                },
                "description": "A list of hourly weather variables to retrieve (e.g., 'temperature_2m', 'precipitation_probability')."
            },
            "daily": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                },
                "description": "A list of daily aggregate weather variables to retrieve (e.g., 'temperature_2m_max', 'uv_index_max')."
            }
        },
        "required": ["location"]
    }
}

class WeatherAgent:
    def __init__(self):
        self.tools = [get_weather_tool]

    async def get_weather(self, location, forecast_days=7, past_days=0, hourly=None, daily=None):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [WEATHER] Getting weather for: '{location}' with params: forecast_days={forecast_days}, past_days={past_days}, hourly={hourly}, daily={daily}")

        try:
            # Step 1: Geocoding
            parts = [p.strip() for p in location.split(',')]
            city = parts[0]
            state = parts[1] if len(parts) > 1 else None
            country = parts[2] if len(parts) > 2 else None

            async with httpx.AsyncClient() as client:
                params = {"name": city, "count": 15, "language": "en", "format": "json"}
                url = "https://geocoding-api.open-meteo.com/v1/search"

                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WEATHER] Requesting Geocoding URL: {url} with params: {params}")

                geo_response = await client.get(url, params=params)

                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WEATHER] Geocoding Response Status: {geo_response.status_code}")
                    print(f"[ADA DEBUG] [WEATHER] Geocoding Response Text: {geo_response.text}")

                geo_response.raise_for_status()
                geo_data = geo_response.json()
                results = geo_data.get("results")

                if not results:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [WEATHER] Geocoding returned no results. Raw response: {geo_response.text}")
                    return f"Could not find location: {location}"

                # Step 2: Filter results if state/country was provided
                if state or country:
                    filtered_results = []
                    for r in results:
                        match = True
                        # State/Admin1 must match if provided
                        if state and not (r.get('admin1') and state.lower() in r.get('admin1').lower()):
                            match = False
                        # Country must match if provided
                        if country and not (r.get('country') and country.lower() in r.get('country').lower()):
                            match = False

                        if match:
                            filtered_results.append(r)

                    # If we found any matches, use the filtered list. Otherwise, stick with the original broad list.
                    if filtered_results:
                        results = filtered_results

                # Step 3: Handle ambiguity
                if len(results) > 1:
                    locations = [
                        f"{i+1}. {r.get('name', 'N/A')}, {r.get('admin1', 'N/A')}, {r.get('country', 'N/A')}"
                        for i, r in enumerate(results)
                    ]
                    return f"Multiple locations found. Please be more specific:\n" + "\n".join(locations)

                lat = results[0]["latitude"]
                lon = results[0]["longitude"]

            # Step 2: Weather Forecast
            params = {
                "latitude": lat,
                "longitude": lon,
                "timezone": "auto"
            }
            if forecast_days is not None:
                params["forecast_days"] = forecast_days
            if past_days is not None:
                params["past_days"] = past_days
            if hourly:
                params["hourly"] = ",".join(hourly)
            if daily:
                params["daily"] = ",".join(daily)

            # Add default daily if nothing is specified
            if not hourly and not daily:
                params["daily"] = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"


            async with httpx.AsyncClient() as client:
                forecast_response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params=params
                )
                forecast_response.raise_for_status()
                weather_data = forecast_response.json()

                # The widget expects a simple daily forecast structure.
                # If daily data is present, format it for the widget.
                # Otherwise, return the full JSON for the model to interpret.
                daily_data = weather_data.get('daily', {})
                if 'time' in daily_data and daily_data['time']:
                    forecast = []
                    num_days = len(daily_data['time'])
                    weather_codes = daily_data.get('weather_code', [None] * num_days)
                    temp_maxes = daily_data.get('temperature_2m_max', [None] * num_days)
                    temp_mins = daily_data.get('temperature_2m_min', [None] * num_days)
                    precipitations = daily_data.get('precipitation_sum', [None] * num_days)

                    for i in range(num_days):
                        forecast.append({
                            "date": daily_data['time'][i],
                            "weather_code": weather_codes[i],
                            "temp_max": temp_maxes[i],
                            "temp_min": temp_mins[i],
                            "precipitation": precipitations[i]
                        })
                    return forecast
                else:
                    return weather_data

        except httpx.HTTPStatusError as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] HTTP error in weather tool: {e}")
            return f"Error processing weather request: {e.response.status_code}"
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to get weather: {e}")
                traceback.print_exc()
            return "Failed to get weather data."