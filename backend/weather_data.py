import requests
from datetime import datetime, timedelta, timezone
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class WeatherData:
    # Airport configurations with coordinates
    AIRPORTS = {
        "KPUW": {"lat": 46.7438, "lon": -117.1096, "name": "Pullman-Moscow"},
        "KSEA": {"lat": 47.4502, "lon": -122.3088, "name": "Seattle-Tacoma"},
        "KBOI": {"lat": 43.5644, "lon": -116.2228, "name": "Boise"}
    }

    def __init__(self):
        # Legacy single-location support (for KPUW)
        self.lat = self.AIRPORTS["KPUW"]["lat"]
        self.lon = self.AIRPORTS["KPUW"]["lon"]

        self.history_url = "https://archive-api.open-meteo.com/v1/archive"
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.last_weather_fetch = None
        self.weather_cache = {}  # Cache by airport code

    def get_weather_for_airport(self, airport_code, past_days=7, forecast_days=3):
        """
        Fetch weather for a single airport.

        Args:
            airport_code: ICAO code (KPUW, KSEA, KBOI)
            past_days: Number of past days to include
            forecast_days: Number of future days to forecast

        Returns:
            dict: {datetime: weather_data}
        """
        if airport_code not in self.AIRPORTS:
            logger.warning(f"Unknown airport code: {airport_code}")
            return {}

        airport = self.AIRPORTS[airport_code]
        weather_map = {}

        try:
            params = {
                "latitude": airport["lat"],
                "longitude": airport["lon"],
                # Request comprehensive weather data
                "hourly": "visibility,wind_speed_10m,wind_direction_10m,wind_gusts_10m,weather_code,temperature_2m,precipitation,snowfall,snow_depth,cloud_cover,relative_humidity_2m,surface_pressure",
                "wind_speed_unit": "kn",
                "temperature_unit": "fahrenheit",
                "precipitation_unit": "inch",
                "timezone": "UTC",
                "past_days": past_days,
                "forecast_days": forecast_days
            }

            response = requests.get(self.forecast_url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            if 'hourly' in data:
                hourly = data['hourly']
                times = hourly['time']
                vis = hourly.get('visibility', [])
                wind = hourly.get('wind_speed_10m', [])
                wind_dir = hourly.get('wind_direction_10m', [])
                wind_gust = hourly.get('wind_gusts_10m', [])
                temp = hourly.get('temperature_2m', [])
                codes = hourly.get('weather_code', [])
                precip = hourly.get('precipitation', [])
                snowfall = hourly.get('snowfall', [])
                snow_depth = hourly.get('snow_depth', [])
                cloud_cover = hourly.get('cloud_cover', [])
                humidity = hourly.get('relative_humidity_2m', [])
                pressure = hourly.get('surface_pressure', [])

                for i, t_str in enumerate(times):
                    dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                    vis_miles = vis[i] * 0.000621371 if (i < len(vis) and vis[i] is not None) else None

                    weather_map[dt] = {
                        # Core fields
                        "visibility_miles": vis_miles,
                        "wind_speed_knots": wind[i] if i < len(wind) else None,
                        "wind_direction": wind_dir[i] if i < len(wind_dir) else None,
                        "temperature_f": temp[i] if i < len(temp) else None,
                        "weather_code": codes[i] if i < len(codes) else None,
                        # Comprehensive fields
                        "wind_gust_knots": wind_gust[i] if i < len(wind_gust) else None,
                        "precipitation_in": precip[i] if i < len(precip) else None,
                        "snow_depth_in": (snow_depth[i] / 2.54) if (i < len(snow_depth) and snow_depth[i] is not None) else None,  # cm to inches
                        "cloud_cover_pct": cloud_cover[i] if i < len(cloud_cover) else None,
                        "humidity_pct": humidity[i] if i < len(humidity) else None,
                        "pressure_mb": pressure[i] if i < len(pressure) else None,
                        "conditions": self._get_conditions_from_code(codes[i] if i < len(codes) else None)
                    }

            logger.info(f"Fetched comprehensive weather for {airport_code} ({airport['name']}): {len(weather_map)} hours")

        except Exception as e:
            logger.error(f"Error fetching weather for {airport_code}: {e}")

        return weather_map

    def get_weather_for_multiple_airports(self, airport_codes, past_days=7, forecast_days=3):
        """
        Fetch weather for multiple airports in parallel.

        Args:
            airport_codes: list of ICAO codes
            past_days: Number of past days to include
            forecast_days: Number of future days to forecast

        Returns:
            dict: {airport_code: {datetime: weather_data}}
        """
        weather_by_airport = {}

        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=len(airport_codes)) as executor:
            future_to_airport = {
                executor.submit(self.get_weather_for_airport, code, past_days, forecast_days): code
                for code in airport_codes
            }

            for future in as_completed(future_to_airport):
                airport_code = future_to_airport[future]
                try:
                    weather_map = future.result()
                    weather_by_airport[airport_code] = weather_map
                except Exception as e:
                    logger.error(f"Failed to fetch weather for {airport_code}: {e}")
                    weather_by_airport[airport_code] = {}

        # Update cache and timestamp
        self.weather_cache = weather_by_airport
        self.last_weather_fetch = datetime.now(timezone.utc)

        return weather_by_airport

    def get_weather_for_flights(self, flights):
        """
        Enriches flight data with weather from all relevant airports (PUW, origin, destination).
        Uses Open-Meteo Forecast API with past_days=7 to cover recent history and future.

        BACKWARD COMPATIBLE: Returns PUW weather in old format for legacy code.
        New format includes origin and destination weather.

        Returns:
            dict: {
                datetime: {
                    "visibility_miles": ...,  # PUW weather (backward compatible)
                    "wind_speed_knots": ...,
                    ...
                    "airports": {
                        "KPUW": {...},
                        "KSEA": {...},
                        "KBOI": {...}
                    }
                }
            }
        """
        if not flights:
            return {}

        # Determine which airports we need
        airport_codes = {"KPUW"}  # Always include PUW
        for flight in flights:
            if flight.get('origin'):
                origin_code = flight['origin']
                if origin_code in self.AIRPORTS:
                    airport_codes.add(origin_code)
            if flight.get('destination'):
                dest_code = flight['destination']
                if dest_code in self.AIRPORTS:
                    airport_codes.add(dest_code)

        # Fetch weather for all airports in parallel
        logger.info(f"Fetching weather for airports: {airport_codes}")
        weather_by_airport = self.get_weather_for_multiple_airports(list(airport_codes))

        # Build unified weather map with backward compatibility
        unified_weather = {}
        puw_weather = weather_by_airport.get("KPUW", {})

        # For each timestamp in PUW weather, create unified record
        for dt, puw_data in puw_weather.items():
            unified_weather[dt] = {
                # Backward compatible: PUW weather at top level
                "visibility_miles": puw_data.get("visibility_miles"),
                "wind_speed_knots": puw_data.get("wind_speed_knots"),
                "wind_direction": puw_data.get("wind_direction"),
                "temperature_f": puw_data.get("temperature_f"),
                "weather_code": puw_data.get("weather_code"),

                # New: Multi-airport weather
                "airports": {
                    "KPUW": puw_data
                }
            }

        # Add other airports' weather to the same timestamps
        for airport_code, weather_map in weather_by_airport.items():
            if airport_code == "KPUW":
                continue

            for dt, weather_data in weather_map.items():
                if dt in unified_weather:
                    unified_weather[dt]["airports"][airport_code] = weather_data
                else:
                    # Create new entry if timestamp doesn't exist
                    unified_weather[dt] = {
                        "visibility_miles": None,
                        "wind_speed_knots": None,
                        "wind_direction": None,
                        "temperature_f": None,
                        "weather_code": None,
                        "airports": {
                            airport_code: weather_data
                        }
                    }

        return unified_weather

    def get_historical_weather_for_date(self, airport_code, date):
        """
        Fetch historical weather for a specific airport and date.
        Uses Open-Meteo Archive API which has data back to 1940.

        Args:
            airport_code: ICAO code
            date: datetime object or ISO date string

        Returns:
            dict: {datetime: weather_data} for that day (24 hours)
        """
        if airport_code not in self.AIRPORTS:
            logger.warning(f"Unknown airport code: {airport_code}")
            return {}

        if isinstance(date, str):
            date = datetime.fromisoformat(date)

        airport = self.AIRPORTS[airport_code]
        weather_map = {}

        try:
            # Format date as YYYY-MM-DD
            date_str = date.strftime("%Y-%m-%d")

            params = {
                "latitude": airport["lat"],
                "longitude": airport["lon"],
                "start_date": date_str,
                "end_date": date_str,
                "hourly": "visibility,wind_speed_10m,wind_direction_10m,weather_code,temperature_2m",
                "wind_speed_unit": "kn",
                "temperature_unit": "fahrenheit",
                "timezone": "UTC"
            }

            response = requests.get(self.history_url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            if 'hourly' in data:
                hourly = data['hourly']
                times = hourly['time']
                vis = hourly['visibility']
                wind = hourly['wind_speed_10m']
                wind_dir = hourly['wind_direction_10m']
                temp = hourly['temperature_2m']
                codes = hourly['weather_code']

                for i, t_str in enumerate(times):
                    dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                    vis_miles = vis[i] * 0.000621371 if vis[i] is not None else None

                    weather_map[dt] = {
                        "visibility_miles": vis_miles,
                        "wind_speed_knots": wind[i],
                        "wind_direction": wind_dir[i],
                        "temperature_f": temp[i],
                        "weather_code": codes[i]
                    }

        except Exception as e:
            logger.error(f"Error fetching historical weather for {airport_code} on {date_str}: {e}")

        return weather_map

    def get_last_weather_sync(self):
        """
        Returns the timestamp of the last weather fetch.
        """
        return self.last_weather_fetch

    def get_taf(self):
        """
        Fetches TAF from NOAA for KPUW.
        """
        try:
            url = "https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/KPUW.TXT"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.error(f"Error fetching TAF: {e}")
        return "TAF Unavailable"

    def _get_conditions_from_code(self, code):
        """
        Convert WMO weather code to human-readable conditions text.

        Args:
            code: WMO weather code (0-99)

        Returns:
            str: Human-readable weather conditions
        """
        if code is None:
            return ""

        # WMO code mappings
        conditions_map = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Light rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Light snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Light rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Light snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with light hail",
            99: "Thunderstorm with heavy hail"
        }

        return conditions_map.get(code, f"Code {code}")

    def check_conditions(self, weather):
        """
        Returns flags for bad weather.
        Works with both old and new weather format.
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

    # Test multi-airport weather fetch
    print("Testing multi-airport weather fetch...")
    weather = wd.get_weather_for_multiple_airports(["KPUW", "KSEA", "KBOI"])

    for airport, data in weather.items():
        print(f"\n{airport}: {len(data)} hours of data")
        if data:
            sample_time = list(data.keys())[0]
            print(f"Sample ({sample_time}): {data[sample_time]}")

    # Test legacy compatibility
    print("\n\nTesting legacy get_weather_for_flights...")
    now = datetime.now(timezone.utc)
    flights = [
        {'scheduled_time': now, 'origin': 'KSEA', 'destination': 'KPUW'},
        {'scheduled_time': now + timedelta(hours=1), 'origin': 'KPUW', 'destination': 'KBOI'}
    ]
    unified = wd.get_weather_for_flights(flights)

    if unified:
        sample_time = list(unified.keys())[0]
        print(f"Sample unified weather: {unified[sample_time]}")
