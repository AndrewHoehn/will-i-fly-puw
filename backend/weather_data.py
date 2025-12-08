import requests
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class WeatherData:
    def __init__(self):
        self.lat = 46.7438
        self.lon = -117.1096
        self.history_url = "https://archive-api.open-meteo.com/v1/archive"
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.last_weather_fetch = None  # Track when weather was last fetched

    def get_weather_for_flights(self, flights):
        """
        Enriches flight data with weather conditions.
        Uses Open-Meteo Forecast API with past_days=7 to cover recent history and future.
        """
        if not flights:
            return {}

        # We always want last 7 days + next 48 hours (2 days)
        # So past_days=7, forecast_days=3 should cover it.
        
        weather_map = {}
        try:
            # Update last fetch timestamp
            self.last_weather_fetch = datetime.now(timezone.utc)

            params = {
                "latitude": self.lat,
                "longitude": self.lon,
                "hourly": "visibility,wind_speed_10m,wind_direction_10m,weather_code,temperature_2m",
                "wind_speed_unit": "kn",
                "temperature_unit": "fahrenheit",
                "timezone": "UTC",
                "past_days": 7,
                "forecast_days": 3
            }

            response = requests.get(self.forecast_url, params=params, timeout=20)
            data = response.json()
            
            if 'hourly' in data:
                hourly = data['hourly']
                times = hourly['time']
                vis = hourly['visibility']
                wind = hourly['wind_speed_10m']
                wind_dir = hourly['wind_direction_10m']
                temp = hourly['temperature_2m']

                for i, t_str in enumerate(times):
                    dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                    vis_miles = vis[i] * 0.000621371 if vis[i] is not None else None

                    weather_map[dt] = {
                        "visibility_miles": vis_miles,
                        "wind_speed_knots": wind[i],
                        "wind_direction": wind_dir[i],
                        "temperature_f": temp[i],
                        "weather_code": hourly['weather_code'][i]
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")

        return weather_map

    def get_last_weather_sync(self):
        """
        Returns the timestamp of the last weather fetch.
        """
        return self.last_weather_fetch

    def get_taf(self):
        """
        Fetches TAF from NOAA.
        """
        try:
            # NOAA Public FTP for TAF
            url = "https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/KPUW.TXT"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.error(f"Error fetching TAF: {e}")
        return "TAF Unavailable"

    def check_conditions(self, weather):
        """
        Returns flags for bad weather.
        """
        flags = []
        if not weather:
            return flags
            
        vis = weather.get('visibility_miles')
        wind = weather.get('wind_speed_knots')
        
        if vis is not None and vis < 1.0:
            flags.append("Low Visibility (< 1 mi)")
        if wind is not None and wind > 30.0:
            flags.append("High Wind (> 30 kn)")
            
        return flags

if __name__ == "__main__":
    wd = WeatherData()
    # Test with dummy flight time
    now = datetime.now(timezone.utc)
    flights = [{'scheduled_time': now}]
    w = wd.get_weather_for_flights(flights)
    print(f"Weather for {now}: {w.get(now.replace(minute=0, second=0, microsecond=0))}")
