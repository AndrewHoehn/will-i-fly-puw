"""
Database migration script to add multi-airport weather support.
This migration is backward-compatible and allows rollback.

Usage:
    python migrate_multiairport_weather.py
"""

import sqlite3
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_path():
    """Determine database path (matches history_db.py logic)"""
    if os.path.exists("/data"):
        return "/data/history.db"
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "history.db")

def migrate():
    """
    Add multi-airport weather columns to historical_flights and history_log tables.
    Preserves existing data by copying to new PUW-specific columns.
    """
    db_path = get_db_path()
    logger.info(f"Migrating database at: {db_path}")

    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if migration already ran
        cursor.execute("PRAGMA table_info(historical_flights)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'puw_visibility_miles' in columns:
            logger.info("Migration already completed. Skipping.")
            conn.close()
            return True

        logger.info("Starting migration...")

        # === HISTORICAL_FLIGHTS TABLE ===

        # Add PUW weather columns (renamed from existing)
        logger.info("Adding PUW weather columns...")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN puw_visibility_miles REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN puw_wind_speed_knots REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN puw_wind_direction REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN puw_temp_f REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN puw_weather_code INTEGER")

        # Add origin airport weather columns
        logger.info("Adding origin airport weather columns...")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN origin_airport TEXT")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN origin_visibility_miles REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN origin_wind_speed_knots REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN origin_wind_direction REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN origin_temp_f REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN origin_weather_code INTEGER")

        # Add destination airport weather columns
        logger.info("Adding destination airport weather columns...")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN dest_airport TEXT")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN dest_visibility_miles REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN dest_wind_speed_knots REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN dest_wind_direction REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN dest_temp_f REAL")
        cursor.execute("ALTER TABLE historical_flights ADD COLUMN dest_weather_code INTEGER")

        # Copy existing weather data to PUW-specific columns
        logger.info("Copying existing weather data to PUW columns...")
        cursor.execute("""
            UPDATE historical_flights
            SET puw_visibility_miles = visibility_miles,
                puw_wind_speed_knots = wind_speed_knots,
                puw_temp_f = temp_f,
                puw_weather_code = weather_code
            WHERE visibility_miles IS NOT NULL
        """)

        # Create indexes for performance
        logger.info("Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_puw_weather
            ON historical_flights (puw_visibility_miles, puw_wind_speed_knots)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_origin_weather
            ON historical_flights (origin_visibility_miles, origin_wind_speed_knots)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dest_weather
            ON historical_flights (dest_visibility_miles, dest_wind_speed_knots)
        """)

        # === HISTORY_LOG TABLE ===

        # Check if history_log needs migration
        cursor.execute("PRAGMA table_info(history_log)")
        log_columns = [col[1] for col in cursor.fetchall()]

        if 'weather_visibility' in log_columns and 'puw_weather_visibility' not in log_columns:
            logger.info("Migrating history_log table...")

            # Add multi-airport columns to history_log
            cursor.execute("ALTER TABLE history_log ADD COLUMN puw_weather_visibility REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN puw_weather_wind REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN puw_weather_temp REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN puw_weather_code INTEGER")

            cursor.execute("ALTER TABLE history_log ADD COLUMN origin_weather_visibility REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN origin_weather_wind REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN origin_weather_temp REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN origin_weather_code INTEGER")

            cursor.execute("ALTER TABLE history_log ADD COLUMN dest_weather_visibility REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN dest_weather_wind REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN dest_weather_temp REAL")
            cursor.execute("ALTER TABLE history_log ADD COLUMN dest_weather_code INTEGER")

            # Copy existing data
            cursor.execute("""
                UPDATE history_log
                SET puw_weather_visibility = weather_visibility,
                    puw_weather_wind = weather_wind,
                    puw_weather_temp = weather_temp,
                    puw_weather_code = weather_code
                WHERE weather_visibility IS NOT NULL
            """)

        # Record migration timestamp
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value)
            VALUES ('multiairport_migration_date', ?)
        """, (datetime.now().isoformat(),))

        conn.commit()
        logger.info("Migration completed successfully!")

        # Print summary
        cursor.execute("SELECT COUNT(*) FROM historical_flights WHERE puw_visibility_miles IS NOT NULL")
        migrated_count = cursor.fetchone()[0]
        logger.info(f"Migrated {migrated_count} historical flight records")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        conn.rollback()
        conn.close()
        return False

def verify_migration():
    """Verify migration completed successfully"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check new columns exist
        cursor.execute("PRAGMA table_info(historical_flights)")
        columns = [col[1] for col in cursor.fetchall()]

        required_columns = [
            'puw_visibility_miles', 'puw_wind_speed_knots', 'puw_wind_direction',
            'origin_visibility_miles', 'origin_wind_speed_knots', 'origin_wind_direction',
            'dest_visibility_miles', 'dest_wind_speed_knots', 'dest_wind_direction'
        ]

        missing = [col for col in required_columns if col not in columns]
        if missing:
            logger.error(f"Migration incomplete. Missing columns: {missing}")
            return False

        # Check data was copied
        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE visibility_miles IS NOT NULL AND puw_visibility_miles IS NULL
        """)
        uncopied = cursor.fetchone()[0]

        if uncopied > 0:
            logger.warning(f"Warning: {uncopied} records have old data but not new data")

        logger.info("Migration verification passed!")
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Multi-Airport Weather Database Migration")
    print("=" * 60)
    print()

    success = migrate()

    if success:
        print()
        print("Verifying migration...")
        verify_migration()
        print()
        print("✓ Migration complete!")
        print()
        print("Note: Old columns (visibility_miles, wind_speed_knots, etc.) are")
        print("preserved for rollback safety. They can be dropped after confirming")
        print("the new system works correctly.")
    else:
        print()
        print("✗ Migration failed. Check logs above.")
        exit(1)
