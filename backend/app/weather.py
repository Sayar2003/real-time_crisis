# backend/app/weather.py
"""
OpenWeatherMap severe weather alert fetcher.
Fetches active weather alerts for major world regions.
"""

import logging
import requests
from backend.app.config import OPENWEATHER_API_KEY

logger = logging.getLogger(__name__)

# Major world cities to monitor for severe weather
MONITORED_CITIES = [
    # Asia Pacific
    {"name": "Tokyo",        "lat": 35.6762,  "lon": 139.6503},
    {"name": "Manila",       "lat": 14.5995,  "lon": 120.9842},
    {"name": "Jakarta",      "lat": -6.2088,  "lon": 106.8456},
    {"name": "Dhaka",        "lat": 23.8103,  "lon": 90.4125},
    {"name": "Mumbai",       "lat": 19.0760,  "lon": 72.8777},
    {"name": "Chennai",      "lat": 13.0827,  "lon": 80.2707},
    {"name": "Bangkok",      "lat": 13.7563,  "lon": 100.5018},
    # Americas
    {"name": "Miami",        "lat": 25.7617,  "lon": -80.1918},
    {"name": "New Orleans",  "lat": 29.9511,  "lon": -90.0715},
    {"name": "Houston",      "lat": 29.7604,  "lon": -95.3698},
    {"name": "Mexico City",  "lat": 19.4326,  "lon": -99.1332},
    # Africa & Middle East
    {"name": "Lagos",        "lat": 6.5244,   "lon": 3.3792},
    {"name": "Nairobi",      "lat": -1.2921,  "lon": 36.8219},
    {"name": "Cairo",        "lat": 30.0444,  "lon": 31.2357},
    # Europe
    {"name": "London",       "lat": 51.5074,  "lon": -0.1278},
    {"name": "Athens",       "lat": 37.9838,  "lon": 23.7275},
]

# Severe weather condition codes from OpenWeatherMap
SEVERE_CONDITIONS = {
    # Thunderstorm
    200: "Thunderstorm with light rain",
    201: "Thunderstorm with rain",
    202: "Thunderstorm with heavy rain",
    210: "Light thunderstorm",
    211: "Thunderstorm",
    212: "Heavy thunderstorm",
    221: "Ragged thunderstorm",
    230: "Thunderstorm with light drizzle",
    231: "Thunderstorm with drizzle",
    232: "Thunderstorm with heavy drizzle",
    # Heavy rain
    502: "Heavy intensity rain",
    503: "Very heavy rain",
    504: "Extreme rain",
    511: "Freezing rain",
    522: "Heavy intensity shower rain",
    # Snow/Extreme
    602: "Heavy snow",
    611: "Sleet",
    622: "Heavy shower snow",
    # Atmosphere
    711: "Smoke",
    721: "Haze",
    731: "Sand/dust whirls",
    741: "Fog",
    751: "Sand",
    761: "Dust",
    762: "Volcanic ash",
    771: "Squalls",
    781: "Tornado",
}

CATEGORY_MAP = {
    2: "Conflict",     # Thunderstorm → treat as severe weather
    5: "Flood",        # Rain
    6: "Flood",        # Snow
    7: "Infrastructure",  # Atmosphere
    781: "Tornado",    # Tornado specifically
    762: "Volcanic",   # Volcanic ash
}


def fetch_severe_weather_alerts() -> list[dict]:
    """
    Fetches current weather for monitored cities and returns
    severe weather events in pipeline-compatible format.
    """
    if not OPENWEATHER_API_KEY:
        logger.warning("OpenWeatherMap API key not set. Skipping weather alerts.")
        return []

    alerts = []

    for city in MONITORED_CITIES:
        try:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={city['lat']}&lon={city['lon']}"
                f"&appid={OPENWEATHER_API_KEY}&units=metric"
            )
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                continue

            data        = response.json()
            weather_id  = data.get("weather", [{}])[0].get("id", 0)
            weather_desc = data.get("weather", [{}])[0].get("description", "")
            temp        = data.get("main", {}).get("temp", 0)
            wind_speed  = data.get("wind", {}).get("speed", 0)
            city_name   = data.get("name", city["name"])

            # Only include severe conditions
            if weather_id not in SEVERE_CONDITIONS and wind_speed < 15:
                continue

            # Determine crisis category
            weather_cat = weather_id // 100
            if weather_id == 781:
                category = "Tornado"
            elif weather_id == 762:
                category = "Volcanic"
            elif weather_cat == 2:
                category = "Flood"  # Thunderstorm can cause flooding
            elif weather_cat in [5, 6]:
                category = "Flood"
            else:
                category = "Infrastructure"

            condition = SEVERE_CONDITIONS.get(weather_id, weather_desc)

            alerts.append({
                "id":           f"weather_{city['name']}_{weather_id}",
                "text":         f"Severe weather alert: {condition} in {city_name}. Wind speed: {wind_speed:.1f}m/s, Temperature: {temp:.1f}°C.",
                "category":     category,
                "lat":          city["lat"],
                "lon":          city["lon"],
                "landmark":     city_name,
                "source":       "openweathermap",
                "geotagged":    True,
                "num_mentions": int(wind_speed),
                "credibility":  0.95,
                "avg_tone":     -5.0,
                "severity_score": 7.0,
                "severity_label": "HIGH",
                "severity_color": "#ffa502",
            })

        except Exception as e:
            logger.debug(f"Weather fetch failed for {city['name']}: {e}")

    logger.info(f"Weather: {len(alerts)} severe weather alerts fetched.")
    return alerts