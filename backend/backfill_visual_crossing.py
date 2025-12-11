"""
Backfill historical weather data using Visual Crossing Weather API.

Visual Crossing provides complete historical weather including visibility,
which Open-Meteo's archive API doesn't include.

Usage:
    python backfill_visual_crossing.py [--limit N] [--dry-run]
    python backfill_visual_crossing.py --skip-until "2025-10-09"
"""

import sqlite3
import argparse
import logging
import time
import requests
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Visual Crossing API key
VISUAL_CROSSING_KEY = "5YXQ8UNJ8S2NHWJBHGWBTHYA5"

# Airport coordinates
AIRPORTS = {
    "KPUW": {"lat": 46.7439, "lon": -117.1095},
    "KSEA": {"lat": 47.4502, "lon": -122.3088},
    "KBOI": {"lat": 43.5644, "lon": -116.2228}
}

def get_db_path():
    """Get database path"""
    import os
    if os.path.exists("/data"):
        return "/data/history.db"
    else:
        return os.path.join(os.path.dirname(__file__), "history.db")

def get_visual_crossing_weather(airport_code, date):
    """
    Fetch historical weather from Visual Crossing for a specific date and airport.

    Args:
        airport_code: ICAO code (KPUW, KSEA, KBOI)
        date: datetime object

    Returns:
        dict with weather data or None if failed
    """
    if airport_code not in AIRPORTS:
        return None

    airport = AIRPORTS[airport_code]
    date_str = date.strftime("%Y-%m-%d")

    # Visual Crossing Timeline API
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{airport['lat']},{airport['lon']}/{date_str}/{date_str}"

    params = {
        "key": VISUAL_CROSSING_KEY,
        "unitGroup": "us",  # US units (mph, F, miles)
        "include": "hours",
        "elements": "datetime,temp,visibility,windspeed,winddir,conditions"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'days' not in data or len(data['days']) == 0:
            logger.warning(f"No data returned for {airport_code} on {date_str}")
            return None

        day_data = data['days'][0]

        # Find the hour closest to the flight time
        target_hour = date.hour
        hours = day_data.get('hours', [])

        if not hours:
            logger.warning(f"No hourly data for {airport_code} on {date_str}")
            return None

        # Find closest hour
        closest_hour = min(hours, key=lambda h: abs(int(h['datetime'].split(':')[0]) - target_hour))

        # Convert to our format
        weather = {
            'visibility_miles': closest_hour.get('visibility'),  # Already in miles
            'wind_speed_knots': closest_hour.get('windspeed') * 0.868976 if closest_hour.get('windspeed') else None,  # mph to knots
            'wind_direction': closest_hour.get('winddir'),
            'temperature_f': closest_hour.get('temp'),
            'weather_code': 0  # Visual Crossing uses text conditions, we'll use 0 for now
        }

        return weather

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.error(f"Rate limit exceeded for {airport_code}")
        else:
            logger.error(f"HTTP error for {airport_code}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching weather for {airport_code} on {date_str}: {e}")
        return None

def backfill_weather(limit=None, dry_run=False, skip_until=None, batch_size=50, delay_seconds=2):
    """
    Backfill multi-airport weather for historical flights using Visual Crossing.

    Args:
        limit: Max number of flights to backfill (None = all)
        dry_run: If True, don't actually update database
        skip_until: Skip flights until this date (YYYY-MM-DD format)
        batch_size: Commit every N flights (helps with resume)
        delay_seconds: Delay between API calls (Visual Crossing allows 1000/day on free tier)
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find flights that need backfilling
    query = """
        SELECT id, flight_number, flight_date, origin_airport, dest_airport
        FROM historical_flights
        WHERE (puw_visibility_miles IS NULL OR origin_visibility_miles IS NULL OR dest_visibility_miles IS NULL)
        AND flight_date IS NOT NULL
        ORDER BY flight_date DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    flights = cursor.fetchall()

    logger.info(f"Found {len(flights)} flights to backfill")

    if skip_until:
        logger.info(f"Will skip flights until date: {skip_until}")

    if dry_run:
        logger.info("DRY RUN - No changes will be made")

    success_count = 0
    error_count = 0
    skipped_count = 0
    batch_count = 0
    skip_mode = bool(skip_until)
    api_calls = 0

    for flight_id, flight_number, flight_date, origin_airport, dest_airport in flights:
        try:
            # Parse date
            if isinstance(flight_date, str):
                date_obj = datetime.fromisoformat(flight_date.replace("Z", "+00:00"))
            else:
                logger.warning(f"Skipping {flight_number} - invalid date format")
                continue

            # Ensure date_obj is timezone-aware (UTC)
            if date_obj.tzinfo is None:
                date_obj = date_obj.replace(tzinfo=timezone.utc)

            flight_date_str = flight_date[:10] if isinstance(flight_date, str) else str(date_obj.date())

            # Skip logic
            if skip_mode:
                if flight_date_str > skip_until:
                    skipped_count += 1
                    if skipped_count % 100 == 0:
                        logger.info(f"Skipped {skipped_count} flights (still at {flight_date_str})...")
                    continue
                elif flight_date_str == skip_until:
                    logger.info(f"Reached skip_until date: {skip_until}. Starting backfill...")
                    skip_mode = False
                else:
                    skip_mode = False

            logger.info(f"[{success_count + error_count + 1}/{len(flights)}] Backfilling {flight_number} on {flight_date_str}")

            # Rate limiting
            if api_calls > 0 and delay_seconds > 0:
                time.sleep(delay_seconds)

            # Fetch weather for all airports
            weather_data = {}

            for airport_code in ["KPUW", origin_airport, dest_airport]:
                if not airport_code or airport_code not in AIRPORTS:
                    continue

                airport_weather = get_visual_crossing_weather(airport_code, date_obj)
                api_calls += 1

                if airport_weather:
                    weather_data[airport_code] = airport_weather
                else:
                    logger.warning(f"No weather data for {airport_code} on {flight_date_str}")

                # Small delay between airports
                time.sleep(0.5)

            if not dry_run:
                # Update database
                update_sql = """
                    UPDATE historical_flights
                    SET
                        puw_visibility_miles = ?,
                        puw_wind_speed_knots = ?,
                        puw_wind_direction = ?,
                        puw_temp_f = ?,
                        puw_weather_code = ?,
                        origin_visibility_miles = ?,
                        origin_wind_speed_knots = ?,
                        origin_wind_direction = ?,
                        origin_temp_f = ?,
                        origin_weather_code = ?,
                        dest_visibility_miles = ?,
                        dest_wind_speed_knots = ?,
                        dest_wind_direction = ?,
                        dest_temp_f = ?,
                        dest_weather_code = ?
                    WHERE id = ?
                """

                puw = weather_data.get("KPUW", {})
                origin = weather_data.get(origin_airport, {})
                dest = weather_data.get(dest_airport, {})

                cursor.execute(update_sql, (
                    puw.get('visibility_miles'),
                    puw.get('wind_speed_knots'),
                    puw.get('wind_direction'),
                    puw.get('temperature_f'),
                    puw.get('weather_code'),
                    origin.get('visibility_miles'),
                    origin.get('wind_speed_knots'),
                    origin.get('wind_direction'),
                    origin.get('temperature_f'),
                    origin.get('weather_code'),
                    dest.get('visibility_miles'),
                    dest.get('wind_speed_knots'),
                    dest.get('wind_direction'),
                    dest.get('temperature_f'),
                    dest.get('weather_code'),
                    flight_id
                ))

            success_count += 1
            batch_count += 1

            # Commit in batches
            if not dry_run and batch_count >= batch_size:
                conn.commit()
                logger.info(f"✓ Committed batch of {batch_count} flights (Total: {success_count} success, {error_count} errors, {api_calls} API calls)")
                batch_count = 0

        except KeyboardInterrupt:
            logger.warning("⚠ Interrupted by user. Committing progress...")
            if not dry_run:
                conn.commit()
            conn.close()
            logger.info(f"Progress saved: {success_count} success, {error_count} errors, {skipped_count} skipped, {api_calls} API calls")
            logger.info(f"To resume, run: python backfill_visual_crossing.py --skip-until \"{flight_date_str}\"")
            raise

        except Exception as e:
            logger.error(f"Error backfilling {flight_number} on {flight_date_str}: {e}")
            error_count += 1
            continue

    # Final commit
    if not dry_run and batch_count > 0:
        conn.commit()
        logger.info(f"✓ Final commit of {batch_count} flights")

    conn.close()

    logger.info(f"Backfill complete: {success_count} success, {error_count} errors, {skipped_count} skipped")
    logger.info(f"Total API calls: {api_calls} (approx cost: ${api_calls * 0.0001:.4f})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill historical weather data using Visual Crossing API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 10 flights
  python backfill_visual_crossing.py --limit 10 --dry-run

  # Backfill all flights (will cost ~$0.42 for 1,401 flights × 3 airports)
  python backfill_visual_crossing.py

  # Resume from specific date
  python backfill_visual_crossing.py --skip-until "2025-10-09"

  # Slower rate (safer, 3 second delay)
  python backfill_visual_crossing.py --delay 3

Note: Visual Crossing free tier allows 1000 API calls/day.
With 3 airports per flight, you can backfill ~330 flights/day.
        """
    )
    parser.add_argument("--limit", type=int, help="Max flights to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database")
    parser.add_argument("--skip-until", type=str, help="Skip flights until this date (YYYY-MM-DD)")
    parser.add_argument("--batch-size", type=int, default=50, help="Commit every N flights (default: 50)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between flights in seconds (default: 2.0)")
    args = parser.parse_args()

    backfill_weather(
        limit=args.limit,
        dry_run=args.dry_run,
        skip_until=args.skip_until,
        batch_size=args.batch_size,
        delay_seconds=args.delay
    )
