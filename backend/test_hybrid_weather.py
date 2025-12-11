"""
Test the hybrid weather approach (METAR + Open-Meteo)
"""

import logging
from weather_data import WeatherData
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_hybrid_weather():
    """Test fetching weather with METAR overlay"""

    wd = WeatherData()

    print("=" * 80)
    print("Testing Hybrid Weather Approach (METAR + Open-Meteo)")
    print("=" * 80)

    # Test fetching weather for PUW
    print("\n1. Fetching weather for KPUW...")
    weather = wd.get_weather_for_airport('KPUW', past_days=0, forecast_days=1)

    # Find the current hour
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)

    # Show current conditions
    print(f"\nCurrent time: {now}")
    print(f"\nWeather around current hour:")
    print("-" * 80)

    for dt in sorted(weather.keys()):
        time_diff = abs((dt - current_hour).total_seconds() / 3600)

        if time_diff <= 3:  # Within 3 hours of now
            data = weather[dt]
            source = data.get('source', 'Open-Meteo')

            print(f"\n{dt} ({source}):")
            print(f"  Visibility: {data['visibility_miles']} miles")
            print(f"  Wind: {data['wind_speed_knots']} kn sustained, {data['wind_gust_knots']} kn gusts")
            print(f"  Temperature: {data['temperature_f']:.1f}°F")
            print(f"  Conditions: {data.get('conditions', 'N/A')}")

            if source == 'METAR':
                print(f"  ✓ Using ACTUAL observation (METAR)")
            else:
                print(f"  ⚠ Using model forecast (Open-Meteo)")

    # Test multi-airport
    print("\n" + "=" * 80)
    print("2. Testing multi-airport weather...")
    multi_weather = wd.get_weather_for_multiple_airports(['KPUW', 'KSEA', 'KBOI'], past_days=0, forecast_days=1)

    for airport in ['KPUW', 'KSEA', 'KBOI']:
        if airport in multi_weather:
            airport_weather = multi_weather[airport]

            # Find current hour weather
            current_weather = airport_weather.get(current_hour)
            if not current_weather:
                # Try to find closest hour
                closest = min(airport_weather.keys(), key=lambda dt: abs((dt - current_hour).total_seconds()))
                current_weather = airport_weather[closest]

            source = current_weather.get('source', 'Open-Meteo')

            print(f"\n{airport} current conditions ({source}):")
            print(f"  Visibility: {current_weather['visibility_miles']} miles")
            print(f"  Wind: {current_weather['wind_speed_knots']} kn, gusts {current_weather['wind_gust_knots']} kn")
            print(f"  Temperature: {current_weather['temperature_f']:.1f}°F")

    print("\n" + "=" * 80)
    print("✓ Test complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_hybrid_weather()
