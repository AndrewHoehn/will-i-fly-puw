"""
BTS Monthly Statistics Ingestion Script

Imports Bureau of Transportation Statistics (BTS) delay data into SQLite database.
Data source: delay_summary/Airline_Delay_Cause.csv (2020-2025)
"""

import csv
import sqlite3
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BTSDataIngester:
    def __init__(self, db_path="history.db"):
        # Handle DATA_DIR environment variable (for production)
        data_dir = os.getenv("DATA_DIR")
        if data_dir:
            if os.path.basename(db_path) == db_path:
                db_path = os.path.join(data_dir, db_path)
        elif os.path.basename(db_path) == db_path:
            # Local development: Use path relative to backend/
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, db_path)

        self.db_path = db_path
        self._init_table()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        """Create BTS monthly statistics table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS bts_monthly_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            carrier TEXT,
            carrier_name TEXT,
            arr_flights REAL,
            arr_del15 REAL,
            carrier_ct REAL,
            weather_ct REAL,
            nas_ct REAL,
            security_ct REAL,
            late_aircraft_ct REAL,
            arr_cancelled REAL,
            arr_diverted REAL,
            arr_delay REAL,
            carrier_delay REAL,
            weather_delay REAL,
            nas_delay REAL,
            security_delay REAL,
            late_aircraft_delay REAL,
            cancellation_rate REAL,
            delay_rate REAL,
            UNIQUE(year, month, carrier)
        );
        """

        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_bts_year_month ON bts_monthly_stats (year, month);
        """

        try:
            with self._get_conn() as conn:
                conn.execute(create_table_sql)
                conn.execute(create_index_sql)
                logger.info("BTS monthly stats table initialized")
        except Exception as e:
            logger.error(f"Failed to init BTS table: {e}")

    def ingest_csv(self, csv_path):
        """
        Ingests BTS delay data from CSV file.

        CSV columns:
        year,month,carrier,carrier_name,airport,airport_name,arr_flights,arr_del15,
        carrier_ct,weather_ct,nas_ct,security_ct,late_aircraft_ct,arr_cancelled,
        arr_diverted,arr_delay,carrier_delay,weather_delay,nas_delay,security_delay,
        late_aircraft_delay
        """
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            return 0

        insert_sql = """
        INSERT OR REPLACE INTO bts_monthly_stats (
            year, month, carrier, carrier_name,
            arr_flights, arr_del15, carrier_ct, weather_ct, nas_ct, security_ct,
            late_aircraft_ct, arr_cancelled, arr_diverted, arr_delay,
            carrier_delay, weather_delay, nas_delay, security_delay, late_aircraft_delay,
            cancellation_rate, delay_rate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        count = 0
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)

                with self._get_conn() as conn:
                    for row in reader:
                        # Parse numeric values
                        arr_flights = float(row['arr_flights']) if row['arr_flights'] else 0
                        arr_cancelled = float(row['arr_cancelled']) if row['arr_cancelled'] else 0
                        arr_del15 = float(row['arr_del15']) if row['arr_del15'] else 0

                        # Calculate rates
                        cancellation_rate = (arr_cancelled / arr_flights * 100) if arr_flights > 0 else 0
                        delay_rate = (arr_del15 / arr_flights * 100) if arr_flights > 0 else 0

                        conn.execute(insert_sql, (
                            int(row['year']),
                            int(row['month']),
                            row['carrier'],
                            row['carrier_name'],
                            float(row['arr_flights']) if row['arr_flights'] else 0,
                            float(row['arr_del15']) if row['arr_del15'] else 0,
                            float(row['carrier_ct']) if row['carrier_ct'] else 0,
                            float(row['weather_ct']) if row['weather_ct'] else 0,
                            float(row['nas_ct']) if row['nas_ct'] else 0,
                            float(row['security_ct']) if row['security_ct'] else 0,
                            float(row['late_aircraft_ct']) if row['late_aircraft_ct'] else 0,
                            arr_cancelled,
                            float(row['arr_diverted']) if row['arr_diverted'] else 0,
                            float(row['arr_delay']) if row['arr_delay'] else 0,
                            float(row['carrier_delay']) if row['carrier_delay'] else 0,
                            float(row['weather_delay']) if row['weather_delay'] else 0,
                            float(row['nas_delay']) if row['nas_delay'] else 0,
                            float(row['security_delay']) if row['security_delay'] else 0,
                            float(row['late_aircraft_delay']) if row['late_aircraft_delay'] else 0,
                            round(cancellation_rate, 2),
                            round(delay_rate, 2)
                        ))
                        count += 1

            logger.info(f"Successfully ingested {count} BTS records")
            return count

        except Exception as e:
            logger.error(f"Failed to ingest BTS data: {e}")
            return 0

    def get_monthly_stats(self):
        """
        Returns BTS monthly statistics ordered by year and month (descending).

        Returns:
            List of dicts with aggregated monthly data
        """
        query_sql = """
        SELECT
            year,
            month,
            carrier_name,
            arr_flights,
            arr_cancelled,
            cancellation_rate,
            arr_del15,
            delay_rate,
            carrier_ct,
            weather_ct,
            nas_ct,
            late_aircraft_ct,
            carrier_delay,
            weather_delay,
            nas_delay,
            late_aircraft_delay
        FROM bts_monthly_stats
        ORDER BY year DESC, month DESC
        """

        try:
            with self._get_conn() as conn:
                cursor = conn.execute(query_sql)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    data = dict(zip(columns, row))
                    # Format month string (e.g., "2024-12")
                    data['month_str'] = f"{data['year']}-{data['month']:02d}"
                    results.append(data)

                return results
        except Exception as e:
            logger.error(f"Failed to fetch BTS stats: {e}")
            return []

    def get_delay_cause_breakdown(self, year=None, month=None):
        """
        Returns delay cause breakdown as percentages.
        If year/month specified, returns data for that period.
        Otherwise returns overall average.
        """
        if year and month:
            query_sql = """
            SELECT
                carrier_ct,
                weather_ct,
                nas_ct,
                late_aircraft_ct,
                arr_del15
            FROM bts_monthly_stats
            WHERE year = ? AND month = ?
            """
            params = (year, month)
        else:
            query_sql = """
            SELECT
                SUM(carrier_ct) as carrier_ct,
                SUM(weather_ct) as weather_ct,
                SUM(nas_ct) as nas_ct,
                SUM(late_aircraft_ct) as late_aircraft_ct,
                SUM(arr_del15) as arr_del15
            FROM bts_monthly_stats
            """
            params = ()

        try:
            with self._get_conn() as conn:
                cursor = conn.execute(query_sql, params)
                row = cursor.fetchone()

                if not row:
                    return {}

                carrier_ct, weather_ct, nas_ct, late_aircraft_ct, total_delays = row

                if total_delays == 0:
                    return {}

                return {
                    "carrier": round((carrier_ct / total_delays) * 100, 1) if carrier_ct else 0,
                    "weather": round((weather_ct / total_delays) * 100, 1) if weather_ct else 0,
                    "nas": round((nas_ct / total_delays) * 100, 1) if nas_ct else 0,
                    "late_aircraft": round((late_aircraft_ct / total_delays) * 100, 1) if late_aircraft_ct else 0
                }
        except Exception as e:
            logger.error(f"Failed to get delay cause breakdown: {e}")
            return {}


def main():
    """Run BTS data ingestion"""
    # Path to BTS CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    csv_path = os.path.join(project_root, "delay_summary", "Airline_Delay_Cause.csv")

    ingester = BTSDataIngester()
    count = ingester.ingest_csv(csv_path)

    if count > 0:
        logger.info(f"✓ Ingested {count} BTS records successfully")

        # Show summary
        stats = ingester.get_monthly_stats()
        logger.info(f"Total months in database: {len(stats)}")

        if stats:
            latest = stats[0]
            logger.info(f"Latest record: {latest['month_str']} - {latest['arr_flights']} flights, {latest['cancellation_rate']}% cancelled")

        # Show overall delay cause breakdown
        breakdown = ingester.get_delay_cause_breakdown()
        if breakdown:
            logger.info("Overall delay cause breakdown:")
            logger.info(f"  Carrier: {breakdown['carrier']}%")
            logger.info(f"  Weather: {breakdown['weather']}%")
            logger.info(f"  NAS: {breakdown['nas']}%")
            logger.info(f"  Late Aircraft: {breakdown['late_aircraft']}%")
    else:
        logger.error("Failed to ingest BTS data")


if __name__ == "__main__":
    main()
