import os
import requests
from datetime import datetime, timezone
from typing_extensions import TypedDict
from typing import Optional
# Removed: from dotenv import load_dotenv
# Environment variables should be loaded by the main application entry point (e.g., api.py)

from agents import function_tool

# Input schema for the weather tool
class WeatherInput(TypedDict):
    location: str
    lat: Optional[float]
    lon: Optional[float]
    unit: str  # 'metric' or 'imperial'

# Define the raw function first
def _fetch_weather_func(data: WeatherInput) -> dict:
    """
    (Internal) Fetches the current weather data for a given location or coordinates using the OpenWeather API.
    Returns a dictionary containing weather data on success, or an error dictionary on failure.
    """
    # log.append("Fetching weather data...") # Removed logging for simplicity
    api_key = os.getenv("OPEN_WEATHER_API_KEY")
    if not api_key:
        # Log the error instead of returning it directly in the tool's result
        print("Error: OPEN_WEATHER_API_KEY not set in environment.")
        return {"error": "Server configuration error: Weather API key not set."}
    # log.append(f"API key found: {'*' * (len(api_key) - 4)}{api_key[-4:]}") # Removed logging

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"appid": api_key, "units": data.get("unit", "metric")}

    if data.get("lat") is not None and data.get("lon") is not None:
        params.update({"lat": data["lat"], "lon": data["lon"]})
    elif data.get("location"):
        params.update({"q": data["location"]})
    else:
        return {"error": "Please provide either a location name or latitude/longitude coordinates."}

    try:
        response = requests.get(base_url, params=params)
        res = response.json()

        if response.status_code == 200:
            return {
                "location": f"{res.get('name')}, {res['sys'].get('country')}",
                "temperature": res["main"].get("temp"),
                "feels_like": res["main"].get("feels_like"),
                "humidity": res["main"].get("humidity"),
                "pressure": res["main"].get("pressure"),
                "weather": res["weather"][0].get("description"),
                "wind_speed": res["wind"].get("speed"),
                "visibility": res.get("visibility", "N/A"),
                "sunrise": datetime.fromtimestamp(res["sys"].get("sunrise"), timezone.utc).isoformat(),
                "sunset": datetime.fromtimestamp(res["sys"].get("sunset"), timezone.utc).isoformat(),
            }
        elif response.status_code == 401:
             print(f"Error: Unauthorized. Check API Key. Response: {res}")
             return {"error": "Server configuration error: Invalid Weather API key."}
        elif response.status_code == 404:
            return {"error": "Location not found. Use a valid name or lat/lon."}
        else:
            print(f"Error: OpenWeather API request failed. Status: {response.status_code}, Response: {res}")
            return {"error": res.get("message", "Unknown error fetching weather data.")}
    except requests.exceptions.RequestException as e:
        print(f"Error: Network error connecting to OpenWeather API. {e}")
        return {"error": f"Network error: {e}"}
    except Exception as e:
        print(f"Error: An unexpected error occurred in fetch_weather. {e}")
        return {"error": f"An unexpected error occurred: {e}"}

# Create the FunctionTool object for the agent runner
fetch_weather_tool = function_tool(_fetch_weather_func)

# Expose the raw function for direct calls if needed (optional, but useful here)
fetch_weather = _fetch_weather_func