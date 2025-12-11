"""
Add comprehensive aviation weather columns to historical_flights table.

This adds fields critical for flight risk assessment:
- Precipitation (rain/snow amount)
- Snow depth on ground
- Wind gusts (critical for landing safety)
- Cloud cover percentage
- Atmospheric pressure
- Humidity
- Weather conditions text
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_path():
    import os
    if os.path.exists("/data"):
        return "/data/history.db"
    else:
        return os.path.join(os.path.dirname(__file__), "history.db")

def migrate():
    db_path = get_db_path()
    logger.info(f"Migrating database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(historical_flights)")
    columns = [row[1] for row in cursor.fetchall()]

    logger.info(f"Current columns: {len(columns)} total")

    # Add comprehensive aviation weather columns for each location (PUW, origin, dest)
    new_columns = [
        # PUW additional weather
        ('puw_wind_gust_knots', 'REAL'),
        ('puw_precipitation_in', 'REAL'),
        ('puw_snow_depth_in', 'REAL'),
        ('puw_cloud_cover_pct', 'REAL'),
        ('puw_pressure_mb', 'REAL'),
        ('puw_humidity_pct', 'REAL'),
        ('puw_conditions', 'TEXT'),

        # Origin airport additional weather
        ('origin_wind_gust_knots', 'REAL'),
        ('origin_precipitation_in', 'REAL'),
        ('origin_snow_depth_in', 'REAL'),
        ('origin_cloud_cover_pct', 'REAL'),
        ('origin_pressure_mb', 'REAL'),
        ('origin_humidity_pct', 'REAL'),
        ('origin_conditions', 'TEXT'),

        # Destination airport additional weather
        ('dest_wind_gust_knots', 'REAL'),
        ('dest_precipitation_in', 'REAL'),
        ('dest_snow_depth_in', 'REAL'),
        ('dest_cloud_cover_pct', 'REAL'),
        ('dest_pressure_mb', 'REAL'),
        ('dest_humidity_pct', 'REAL'),
        ('dest_conditions', 'TEXT'),
    ]

    added = 0
    for col_name, col_type in new_columns:
        if col_name not in columns:
            logger.info(f"Adding column: {col_name} {col_type}")
            cursor.execute(f"ALTER TABLE historical_flights ADD COLUMN {col_name} {col_type}")
            added += 1
        else:
            logger.info(f"Column {col_name} already exists, skipping")

    conn.commit()
    conn.close()

    logger.info(f"✓ Migration complete! Added {added} new columns")

if __name__ == "__main__":
    migrate()
