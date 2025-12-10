"""
Backfill historical weather data for SEA and BOI airports.

This script fetches historical weather for existing flight records
and populates the multi-airport weather columns.

Usage:
    python backfill_historical_weather.py [--limit N] [--dry-run]
"""

import sqlite3
import argparse
import logging
from datetime import datetime, timezone
from weather_data import WeatherData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_path():
    """Get database path"""
    import os
    if os.path.exists("/data"):
        return "/data/history.db"
    else:
        return os.path.join(os.path.dirname(__file__), "history.db")

def backfill_weather(limit=None, dry_run=False):
    """
    Backfill multi-airport weather for historical flights.

    Args:
        limit: Max number of flights to backfill (None = all)
        dry_run: If True, don't actually update database
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    wd = WeatherData()

    # Find flights that need backfilling
    query = """
        SELECT id, flight_number, flight_date, origin_airport, dest_airport
        FROM historical_flights
        WHERE (origin_visibility_miles IS NULL OR dest_visibility_miles IS NULL)
        AND flight_date IS NOT NULL
        ORDER BY flight_date DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    flights = cursor.fetchall()

    logger.info(f"Found {len(flights)} flights to backfill")

    if dry_run:
        logger.info("DRY RUN - No changes will be made")

    success_count = 0
    error_count = 0

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

            logger.info(f"Backfilling {flight_number} on {flight_date[:10]}")

            # Fetch weather for all airports on that date
            weather_data = {}

            for airport_code in ["KPUW", origin_airport, dest_airport]:
                if not airport_code or airport_code not in wd.AIRPORTS:
                    continue

                airport_weather = wd.get_historical_weather_for_date(airport_code, date_obj)
                if airport_weather:
                    # Get weather closest to flight time
                    closest_weather = min(
                        airport_weather.items(),
                        key=lambda x: abs((x[0] - date_obj).total_seconds())
                    )[1]
                    weather_data[airport_code] = closest_weather
                else:
                    logger.warning(f"No weather data for {airport_code} on {flight_date[:10]}")

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

        except Exception as e:
            logger.error(f"Error backfilling {flight_number}: {e}")
            error_count += 1
            continue

    if not dry_run:
        conn.commit()

    conn.close()

    logger.info(f"Backfill complete: {success_count} success, {error_count} errors")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill historical weather data")
    parser.add_argument("--limit", type=int, help="Max flights to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database")
    args = parser.parse_args()

    backfill_weather(limit=args.limit, dry_run=args.dry_run)
