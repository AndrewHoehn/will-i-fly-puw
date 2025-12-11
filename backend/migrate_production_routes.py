"""
Migrate production database to add route mappings.

This script should be run ON THE PRODUCTION SERVER to populate
origin_airport and dest_airport based on flight number patterns
from the active_flights table.
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_path():
    """Get database path"""
    import os
    if os.path.exists("/data"):
        return "/data/history.db"
    else:
        return os.path.join(os.path.dirname(__file__), "history.db")

def build_flight_route_mapping(conn):
    """
    Build a mapping of flight numbers to routes from active_flights.

    Returns:
        dict: {flight_number: (origin, destination)}
    """
    cursor = conn.cursor()

    # Get the most common route for each flight number
    cursor.execute("""
        SELECT number, origin, destination, COUNT(*) as freq
        FROM active_flights
        WHERE origin IS NOT NULL AND destination IS NOT NULL
        GROUP BY number, origin, destination
        ORDER BY number, freq DESC
    """)

    routes = {}
    for row in cursor.fetchall():
        flight_num = row[0]
        origin = row[1]
        dest = row[2]
        freq = row[3]

        # Keep the most frequent route for each flight number
        if flight_num not in routes:
            routes[flight_num] = (origin, dest)
            logger.info(f"{flight_num}: {origin} → {dest} ({freq} occurrences)")

    return routes

def migrate_production():
    """Update production historical_flights with origin/destination."""
    db_path = get_db_path()
    logger.info(f"Migrating production database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Build route mapping
    logger.info("Building flight number → route mapping from active_flights...")
    route_map = build_flight_route_mapping(conn)
    logger.info(f"Found {len(route_map)} unique flight number routes")

    # Get all historical flights without routes
    cursor.execute("""
        SELECT id, flight_number
        FROM historical_flights
        WHERE origin_airport IS NULL OR dest_airport IS NULL
    """)

    flights_to_update = cursor.fetchall()
    logger.info(f"Found {len(flights_to_update)} historical flights to update")

    updated = 0
    unknown = 0

    for flight_id, flight_number in flights_to_update:
        if flight_number in route_map:
            origin, dest = route_map[flight_number]

            cursor.execute("""
                UPDATE historical_flights
                SET origin_airport = ?, dest_airport = ?
                WHERE id = ?
            """, (origin, dest, flight_id))

            updated += 1

            if updated % 100 == 0:
                logger.info(f"Updated {updated} flights...")
        else:
            unknown += 1
            if unknown <= 10:
                logger.warning(f"Unknown route for flight {flight_number}")

    conn.commit()
    conn.close()

    logger.info(f"✓ Migration complete: {updated} flights updated, {unknown} unknown")
    return updated, unknown

if __name__ == "__main__":
    migrate_production()
