"""
Import historical flight data from CSV into the historical_flights table.
"""
import csv
import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_historical_data(csv_path, db_path="history.db"):
    """
    Import historical flight data from CSV into the database.

    CSV columns: flight_number, airline, flight_date, direction, scheduled_time_local,
    scheduled_time_utc, actual_time_local, actual_time_utc, status, is_cancelled,
    origin_icao, origin_iata, destination_icao, destination_iata, aircraft_model,
    aircraft_reg, relevant_timestamp, actual_temp_c, actual_wind_speed_kmh,
    actual_wind_gusts_kmh, actual_precipitation_mm, actual_snowfall_cm,
    actual_visibility_m, actual_cloud_cover_pct, actual_weather_code, ...
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing historical data (optional - comment out if you want to keep it)
    # cursor.execute("DELETE FROM historical_flights")
    # logger.info("Cleared existing historical_flights data")

    imported = 0
    skipped = 0

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                # Parse boolean
                is_cancelled = row['is_cancelled'].strip().lower() in ('true', '1', 'yes')

                # Convert visibility from meters to miles
                visibility_m = row.get('actual_visibility_m', '')
                visibility_miles = None
                if visibility_m and visibility_m.strip():
                    visibility_miles = float(visibility_m) * 0.000621371

                # Convert wind speed from km/h to knots
                wind_kmh = row.get('actual_wind_speed_kmh', '')
                wind_knots = None
                if wind_kmh and wind_kmh.strip():
                    wind_knots = float(wind_kmh) * 0.539957

                # Convert temperature from C to F
                temp_c = row.get('actual_temp_c', '')
                temp_f = None
                if temp_c and temp_c.strip():
                    temp_f = float(temp_c) * 9/5 + 32

                # Snowfall
                snowfall_cm = row.get('actual_snowfall_cm', '')
                snowfall = None
                if snowfall_cm and snowfall_cm.strip():
                    snowfall = float(snowfall_cm)

                # Weather code
                weather_code = row.get('actual_weather_code', '')
                wcode = None
                if weather_code and weather_code.strip():
                    wcode = int(weather_code)

                # Insert into database
                cursor.execute("""
                    INSERT INTO historical_flights (
                        flight_number, flight_date, is_cancelled,
                        visibility_miles, wind_speed_knots, temp_f,
                        snowfall_cm, weather_code
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['flight_number'],
                    row['flight_date'],
                    1 if is_cancelled else 0,
                    visibility_miles,
                    wind_knots,
                    temp_f,
                    snowfall,
                    wcode
                ))

                imported += 1

                if imported % 100 == 0:
                    logger.info(f"Imported {imported} records...")

            except Exception as e:
                logger.warning(f"Skipped row due to error: {e}")
                logger.warning(f"Row data: {row}")
                skipped += 1
                continue

    conn.commit()
    conn.close()

    logger.info(f"Import complete! Imported: {imported}, Skipped: {skipped}")

    return imported, skipped

if __name__ == "__main__":
    csv_path = "../historical_flight_data/kpuw_master_training_data.csv"
    imported, skipped = import_historical_data(csv_path)
    print(f"\nImport Summary:")
    print(f"  Successfully imported: {imported}")
    print(f"  Skipped (errors): {skipped}")
