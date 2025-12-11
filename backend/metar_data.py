"""
METAR Aviation Weather Data

Fetches real-time METAR observations from NOAA Aviation Weather API.
This provides actual observed weather conditions at airports, which is more
accurate than model-based forecasts for current conditions.

METAR data includes:
- Actual visibility (statute miles)
- Wind speed and gusts (knots)
- Wind direction (degrees)
- Temperature and dewpoint (Celsius)
- Altimeter setting (millibars)
- Weather phenomena (rain, fog, etc.)

Source: https://aviationweather.gov/data/api/
"""

import requests
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class METARDataSource:
    """Fetch METAR observations from NOAA Aviation Weather"""

    def __init__(self):
        self.base_url = "https://aviationweather.gov/api/data/metar"

        # Airport ICAO codes (METAR uses ICAO)
        self.AIRPORTS = {
            'KPUW': {'name': 'Pullman-Moscow', 'lat': 46.7439, 'lon': -117.1095},
            'KSEA': {'name': 'Seattle-Tacoma', 'lat': 47.4502, 'lon': -122.3088},
            'KBOI': {'name': 'Boise', 'lat': 43.5644, 'lon': -116.2228}
        }

    def _celsius_to_fahrenheit(self, celsius: Optional[float]) -> Optional[float]:
        """Convert Celsius to Fahrenheit"""
        return (celsius * 9/5) + 32 if celsius is not None else None

    def _parse_weather_conditions(self, wx_string: Optional[str]) -> str:
        """
        Parse METAR weather phenomena into readable conditions

        Common codes:
        - RA: Rain
        - SN: Snow
        - FG: Fog
        - BR: Mist
        - TS: Thunderstorm
        - DZ: Drizzle
        - FZ: Freezing
        - -: Light
        - +: Heavy
        """
        if not wx_string:
            return ''

        # Common weather phenomena mappings
        conditions = []
        wx_upper = wx_string.upper()

        # Intensity
        intensity = ''
        if wx_upper.startswith('-'):
            intensity = 'Light '
        elif wx_upper.startswith('+'):
            intensity = 'Heavy '

        # Phenomena
        if 'TS' in wx_upper:
            conditions.append('Thunderstorm')
        if 'FG' in wx_upper:
            conditions.append('Fog')
        if 'BR' in wx_upper:
            conditions.append('Mist')
        if 'RA' in wx_upper:
            conditions.append(f'{intensity}Rain'.strip())
        if 'SN' in wx_upper:
            conditions.append(f'{intensity}Snow'.strip())
        if 'DZ' in wx_upper:
            conditions.append(f'{intensity}Drizzle'.strip())
        if 'FZ' in wx_upper and 'RA' in wx_upper:
            conditions.append('Freezing Rain')
        elif 'FZ' in wx_upper:
            conditions.append('Freezing')
        if 'IC' in wx_upper:
            conditions.append('Ice')

        return ', '.join(conditions) if conditions else wx_string

    def get_current_metar(self, airport_codes: list) -> Dict[str, Optional[Dict]]:
        """
        Fetch current METAR for one or more airports

        Args:
            airport_codes: List of ICAO codes (e.g., ['KPUW', 'KSEA'])

        Returns:
            Dict mapping airport code to weather data dict, or None if unavailable
        """
        if not airport_codes:
            return {}

        results = {}

        try:
            # Build comma-separated list
            ids = ','.join(airport_codes)

            params = {
                'ids': ids,
                'format': 'json'
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse each METAR
            for metar in data:
                icao = metar.get('icaoId')
                if not icao:
                    continue

                # Extract weather data
                weather = {
                    # Core fields matching our schema
                    'visibility_miles': metar.get('visib'),  # Already in statute miles
                    'wind_speed_knots': metar.get('wspd'),  # Already in knots
                    'wind_direction': metar.get('wdir'),  # Degrees
                    'temperature_f': self._celsius_to_fahrenheit(metar.get('temp')),
                    'weather_code': 0,  # METAR uses text, not WMO codes

                    # Comprehensive fields
                    'wind_gust_knots': metar.get('wgst'),  # Gusts in knots
                    'precipitation_in': metar.get('precip') if metar.get('precip') else 0,  # Last hour precip
                    'snow_depth_in': None,  # METAR doesn't include snow depth on ground
                    'cloud_cover_pct': None,  # Would need to parse cloud layers
                    'pressure_mb': metar.get('altim'),  # Altimeter in millibars
                    'humidity_pct': self._calculate_humidity(
                        metar.get('temp'),
                        metar.get('dewp')
                    ),
                    'conditions': self._parse_weather_conditions(metar.get('wxString')),

                    # Metadata
                    'observation_time': metar.get('reportTime'),
                    'raw_metar': metar.get('rawOb'),
                    'source': 'METAR'
                }

                results[icao] = weather
                logger.info(f"Retrieved METAR for {icao}: vis={weather['visibility_miles']}mi, "
                          f"wind={weather['wind_speed_knots']}kn, gusts={weather['wind_gust_knots']}kn")

            # Fill in None for requested airports with no data
            for code in airport_codes:
                if code not in results:
                    results[code] = None
                    logger.warning(f"No METAR data available for {code}")

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching METAR data: {e}")
            return {code: None for code in airport_codes}
        except Exception as e:
            logger.error(f"Unexpected error parsing METAR: {e}")
            return {code: None for code in airport_codes}

    def _calculate_humidity(self, temp_c: Optional[float], dewpoint_c: Optional[float]) -> Optional[float]:
        """
        Calculate relative humidity from temperature and dewpoint

        Using Magnus-Tetens approximation:
        RH = 100 * exp((17.625 * Td)/(243.04 + Td)) / exp((17.625 * T)/(243.04 + T))
        """
        if temp_c is None or dewpoint_c is None:
            return None

        try:
            import math

            # Magnus-Tetens constants
            a = 17.625
            b = 243.04

            # Calculate vapor pressures
            dewpoint_vp = math.exp((a * dewpoint_c) / (b + dewpoint_c))
            temp_vp = math.exp((a * temp_c) / (b + temp_c))

            # Relative humidity
            rh = 100 * (dewpoint_vp / temp_vp)

            # Clamp to valid range
            return max(0, min(100, rh))
        except Exception as e:
            logger.warning(f"Error calculating humidity: {e}")
            return None

    def is_metar_recent(self, observation_time: Optional[str], max_age_minutes: int = 90) -> bool:
        """
        Check if METAR observation is recent enough to use

        Args:
            observation_time: ISO 8601 timestamp from METAR
            max_age_minutes: Maximum age in minutes (default 90 = 1.5 hours)

        Returns:
            True if observation is recent enough
        """
        if not observation_time:
            return False

        try:
            obs_time = datetime.fromisoformat(observation_time.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age = (now - obs_time).total_seconds() / 60

            return age <= max_age_minutes
        except Exception as e:
            logger.warning(f"Error checking METAR age: {e}")
            return False


if __name__ == "__main__":
    # Test the METAR data source
    logging.basicConfig(level=logging.INFO)

    metar = METARDataSource()

    # Test fetching current METAR
    print("Fetching current METAR for PUW, SEA, BOI...")
    data = metar.get_current_metar(['KPUW', 'KSEA', 'KBOI'])

    for airport, weather in data.items():
        if weather:
            print(f"\n{airport}:")
            print(f"  Visibility: {weather['visibility_miles']} mi")
            print(f"  Wind: {weather['wind_speed_knots']} kn, gusts {weather['wind_gust_knots']} kn")
            print(f"  Temperature: {weather['temperature_f']:.1f}°F")
            print(f"  Conditions: {weather['conditions']}")
            print(f"  Raw METAR: {weather['raw_metar']}")

            if metar.is_metar_recent(weather['observation_time']):
                print("  ✓ Observation is recent")
            else:
                print("  ⚠ Observation is stale")
        else:
            print(f"\n{airport}: No data available")
