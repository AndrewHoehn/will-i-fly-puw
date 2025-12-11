"""
Migrate historical_flights table to add multi-airport weather columns.
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

    logger.info(f"Current columns: {columns}")

    # Add multi-airport weather columns if they don't exist
    new_columns = [
        ('origin_airport', 'TEXT'),
        ('dest_airport', 'TEXT'),
        ('puw_visibility_miles', 'REAL'),
        ('puw_wind_speed_knots', 'REAL'),
        ('puw_wind_direction', 'INTEGER'),
        ('puw_temp_f', 'REAL'),
        ('puw_weather_code', 'INTEGER'),
        ('origin_visibility_miles', 'REAL'),
        ('origin_wind_speed_knots', 'REAL'),
        ('origin_wind_direction', 'INTEGER'),
        ('origin_temp_f', 'REAL'),
        ('origin_weather_code', 'INTEGER'),
        ('dest_visibility_miles', 'REAL'),
        ('dest_wind_speed_knots', 'REAL'),
        ('dest_wind_direction', 'INTEGER'),
        ('dest_temp_f', 'REAL'),
        ('dest_weather_code', 'INTEGER')
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            logger.info(f"Adding column: {col_name} {col_type}")
            cursor.execute(f"ALTER TABLE historical_flights ADD COLUMN {col_name} {col_type}")
        else:
            logger.info(f"Column {col_name} already exists, skipping")

    conn.commit()
    conn.close()

    logger.info("✓ Migration complete!")

if __name__ == "__main__":
    migrate()
