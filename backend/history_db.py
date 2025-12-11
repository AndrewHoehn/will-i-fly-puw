import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class HistoryDatabase:
    def __init__(self, db_path=None):
        # 1. Determine base path
        if db_path is None:
            if os.path.exists("/data"):
                self.db_path = "/data/history.db"
            else:
                self.db_path = "history.db"
        else:
            self.db_path = db_path

        # 2. Apply DATA_DIR or local path if it's just a filename
        if os.path.basename(self.db_path) == self.db_path:
            data_dir = os.getenv("DATA_DIR")
            if data_dir:
                self.db_path = os.path.join(data_dir, self.db_path)
            else:
                # Local development: Use path relative to this file
                base_dir = os.path.dirname(os.path.abspath(__file__))
                self.db_path = os.path.join(base_dir, self.db_path)

        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Creates the tables if they don't exist."""
        # Historical flights table (completed flights for analysis)
        create_historical_sql = """
        CREATE TABLE IF NOT EXISTS historical_flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_number TEXT,
            flight_date TEXT,
            is_cancelled INTEGER,
            visibility_miles REAL,
            wind_speed_knots REAL,
            temp_f REAL,
            snowfall_cm REAL,
            weather_code INTEGER,
            puw_visibility_miles REAL,
            puw_wind_speed_knots REAL,
            puw_wind_direction REAL,
            puw_temp_f REAL,
            puw_weather_code INTEGER,
            origin_airport TEXT,
            origin_visibility_miles REAL,
            origin_wind_speed_knots REAL,
            origin_wind_direction REAL,
            origin_temp_f REAL,
            origin_weather_code INTEGER,
            dest_airport TEXT,
            dest_visibility_miles REAL,
            dest_wind_speed_knots REAL,
            dest_wind_direction REAL,
            dest_temp_f REAL,
            dest_weather_code INTEGER,
            puw_wind_gust_knots REAL,
            puw_precipitation_in REAL,
            puw_snow_depth_in REAL,
            puw_cloud_cover_pct REAL,
            puw_pressure_mb REAL,
            puw_humidity_pct REAL,
            puw_conditions TEXT,
            origin_wind_gust_knots REAL,
            origin_precipitation_in REAL,
            origin_snow_depth_in REAL,
            origin_cloud_cover_pct REAL,
            origin_pressure_mb REAL,
            origin_humidity_pct REAL,
            origin_conditions TEXT,
            dest_wind_gust_knots REAL,
            dest_precipitation_in REAL,
            dest_snow_depth_in REAL,
            dest_cloud_cover_pct REAL,
            dest_pressure_mb REAL,
            dest_humidity_pct REAL,
            dest_conditions TEXT
        );
        """

        # Active flights table (current/upcoming flights cache)
        create_active_sql = """
        CREATE TABLE IF NOT EXISTS active_flights (
            flight_id TEXT PRIMARY KEY,
            number TEXT,
            airline TEXT,
            origin TEXT,
            destination TEXT,
            scheduled_time_str TEXT,
            actual_time_str TEXT,
            revised_time_str TEXT,
            runway_time_str TEXT,
            status TEXT,
            type TEXT,
            aircraft_reg TEXT,
            aircraft_model TEXT,
            last_updated TEXT
        );
        """

        # Metadata table for tracking sync times
        create_metadata_sql = """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """

        # History log table for prediction tracking
        create_history_log_sql = """
        CREATE TABLE IF NOT EXISTS history_log (
            flight_id TEXT PRIMARY KEY,
            number TEXT,
            scheduled_time TEXT,
            actual_time TEXT,
            status TEXT,
            predicted_risk REAL,
            predicted_level TEXT,
            weather_visibility REAL,
            weather_wind REAL,
            weather_temp REAL,
            weather_code INTEGER,
            timestamp TEXT
        );
        """

        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_weather ON historical_flights (visibility_miles, wind_speed_knots);
        """

        create_active_time_index = """
        CREATE INDEX IF NOT EXISTS idx_active_scheduled ON active_flights (scheduled_time_str);
        """

        try:
            with self._get_conn() as conn:
                conn.execute(create_historical_sql)
                conn.execute(create_active_sql)
                conn.execute(create_metadata_sql)
                conn.execute(create_history_log_sql)
                conn.execute(create_index_sql)
                conn.execute(create_active_time_index)
        except Exception as e:
            logger.error(f"Failed to init history DB: {e}")

    def get_daily_flight_counts(self, days_back=7):
        """
        Returns a dictionary of { 'YYYY-MM-DD': count } for the last N days.
        Based on UTC scheduled time.
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # SQLite query to group by date (substr first 10 chars of ISO string)
            # We look at active_flights
            query = """
            SELECT substr(scheduled_time_str, 1, 10) as day, COUNT(*) as count 
            FROM active_flights 
            WHERE scheduled_time_str >= date('now', ?) 
            GROUP BY day
            """
            
            cursor.execute(query, (f'-{days_back} days',))
            rows = cursor.fetchall()
            conn.close()
            
            return {row[0]: row[1] for row in rows if row[0]}
        except Exception as e:
            logger.error(f"Failed to get daily flight counts: {e}")
            return {}

    def add_flight(self, data):
        """
        data: dict with keys matching columns
        """
        # Check for duplicates (Flight Number + Date)
        check_sql = "SELECT id FROM historical_flights WHERE flight_number = ? AND flight_date = ?"
        insert_sql = """
        INSERT INTO historical_flights (
            flight_number, flight_date, is_cancelled, 
            visibility_miles, wind_speed_knots, temp_f, 
            snowfall_cm, weather_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_conn() as conn:
                # Check
                cursor = conn.execute(check_sql, (data.get('flight_number'), data.get('flight_date')))
                if cursor.fetchone():
                    return # Already exists

                # Insert
                conn.execute(insert_sql, (
                    data.get('flight_number'),
                    data.get('flight_date'),
                    1 if data.get('is_cancelled') else 0,
                    data.get('visibility_miles'),
                    data.get('wind_speed_knots'),
                    data.get('temp_f'),
                    data.get('snowfall_cm'),
                    data.get('weather_code')
                ))
        except Exception as e:
            logger.error(f"Failed to insert flight: {e}")

    def find_similar_flights(self, visibility=None, wind=None, temp=None):
        """
        Finds flights with similar weather conditions.
        Returns (total_count, cancelled_count)
        """
        # Base query
        sql = "SELECT count(*), sum(is_cancelled) FROM historical_flights WHERE 1=1"
        params = []

        # Visibility Logic (Find flights with WORSE or SIMILAR visibility)
        # If vis is low (< 2mi), look for flights with vis <= current + 0.5
        if visibility is not None:
            if visibility < 2.0:
                sql += " AND visibility_miles <= ?"
                params.append(visibility + 0.5)
            else:
                # For good visibility, just ensure it wasn't terrible
                sql += " AND visibility_miles > 2.0"

        # Wind Logic (Find flights with HIGHER or SIMILAR wind)
        if wind is not None:
            if wind > 15:
                sql += " AND wind_speed_knots >= ?"
                params.append(wind - 5)
        
        # Temp/Snow Logic (Freezing)
        if temp is not None and temp < 34:
             sql += " AND temp_f < 34"

        try:
            with self._get_conn() as conn:
                cursor = conn.execute(sql, params)
                row = cursor.fetchone()
                if row:
                    total = row[0] or 0
                    cancelled = row[1] or 0
                    return total, cancelled
        except Exception as e:
            logger.error(f"Query failed: {e}")
        
        return 0, 0

    def get_recent_stats(self, days=30):
        """
        Returns cancellation stats for the last N days.
        """
        try:
            from datetime import datetime, timedelta
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Calculate cutoff date
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            c.execute("""
                SELECT COUNT(*), SUM(CASE WHEN is_cancelled THEN 1 ELSE 0 END)
                FROM historical_flights
                WHERE flight_date >= ?
            """, (cutoff,))

            row = c.fetchone()
            conn.close()

            total = row[0] or 0
            cancelled = row[1] or 0
            rate = (cancelled / total * 100) if total > 0 else 0.0

            return {
                "total": total,
                "cancelled": cancelled,
                "rate": rate
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"total": 0, "cancelled": 0, "rate": 0.0}

    # Active Flights Management
    def upsert_active_flight(self, flight_data):
        """
        Insert or update an active flight.
        flight_data: dict with flight information
        """
        upsert_sql = """
        INSERT OR REPLACE INTO active_flights (
            flight_id, number, airline, origin, destination,
            scheduled_time_str, actual_time_str, revised_time_str, runway_time_str,
            status, type, aircraft_reg, aircraft_model, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_conn() as conn:
                from datetime import datetime, timezone
                conn.execute(upsert_sql, (
                    flight_data.get('id'),
                    flight_data.get('number'),
                    flight_data.get('airline'),
                    flight_data.get('origin'),
                    flight_data.get('destination'),
                    flight_data.get('scheduled_time_str'),
                    flight_data.get('actual_time_str'),
                    flight_data.get('revised_time_str'),
                    flight_data.get('runway_time_str'),
                    flight_data.get('status'),
                    flight_data.get('type'),
                    flight_data.get('aircraft_reg'),
                    flight_data.get('aircraft_model'),
                    datetime.now(timezone.utc).isoformat()
                ))
        except Exception as e:
            logger.error(f"Failed to upsert active flight: {e}")

    def get_all_active_flights(self):
        """
        Returns all active flights from the database.
        Maps flight_id to id for backward compatibility.
        """
        try:
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM active_flights")
                rows = cursor.fetchall()
                flights = []
                for row in rows:
                    flight = dict(row)
                    # Map flight_id to id for backward compatibility
                    if 'flight_id' in flight:
                        flight['id'] = flight['flight_id']
                    flights.append(flight)
                return flights
        except Exception as e:
            logger.error(f"Failed to fetch active flights: {e}")
            return []

    def cleanup_old_flights(self, days_back=7):
        """
        Remove active flights older than specified days.
        """
        try:
            from datetime import datetime, timedelta, timezone
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

            with self._get_conn() as conn:
                conn.execute("""
                    DELETE FROM active_flights
                    WHERE scheduled_time_str < ?
                """, (cutoff,))
                deleted = conn.total_changes
                logger.info(f"Cleaned up {deleted} old active flights")
        except Exception as e:
            logger.error(f"Failed to cleanup old flights: {e}")

    # Metadata Management
    def set_metadata(self, key, value):
        """
        Store a metadata value.
        """
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO metadata (key, value)
                    VALUES (?, ?)
                """, (key, value))
        except Exception as e:
            logger.error(f"Failed to set metadata: {e}")

    def get_metadata(self, key, default=None):
        """
        Retrieve a metadata value.
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return default

    # History Log Management (for prediction tracking)
    def log_prediction(self, flight, weather, risk_score):
        """
        Logs a flight prediction to the history_log table.
        """
        if not risk_score:
            return

        insert_sql = """
        INSERT OR REPLACE INTO history_log (
            flight_id, number, scheduled_time, actual_time, status,
            predicted_risk, predicted_level,
            weather_visibility, weather_wind, weather_temp, weather_code,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            from datetime import datetime, timezone

            # Extract weather data
            weather_dict = weather.dict() if hasattr(weather, 'dict') else weather
            vis = weather_dict.get('visibility_miles') if weather_dict else None
            wind = weather_dict.get('wind_speed_knots') if weather_dict else None
            temp = weather_dict.get('temperature_f') if weather_dict else None
            code = weather_dict.get('weather_code') if weather_dict else None

            with self._get_conn() as conn:
                conn.execute(insert_sql, (
                    flight.get('id'),
                    flight.get('number'),
                    flight.get('scheduled_time_str'),
                    flight.get('actual_time_str'),
                    flight.get('status'),
                    risk_score.score if hasattr(risk_score, 'score') else risk_score,
                    risk_score.risk_level if hasattr(risk_score, 'risk_level') else None,
                    vis, wind, temp, code,
                    datetime.now(timezone.utc).isoformat()
                ))
        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")

    def get_historical_predictions(self):
        """
        Returns a map of flight_id -> {score, level} from the history log.
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    SELECT flight_id, predicted_risk, predicted_level
                    FROM history_log
                """)
                rows = cursor.fetchall()
                return {
                    row[0]: {
                        'score': row[1],
                        'level': row[2]
                    }
                    for row in rows if row[0]
                }
        except Exception as e:
            logger.error(f"Failed to get historical predictions: {e}")
            return {}

    def get_monthly_statistics(self):
        """
        Returns monthly statistics from historical_flights table.
        Groups by year-month and returns total flights, cancellations, and rate.
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    SELECT
                        strftime('%Y-%m', flight_date) as month,
                        COUNT(*) as total_flights,
                        SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) as cancelled,
                        AVG(visibility_miles) as avg_visibility,
                        AVG(wind_speed_knots) as avg_wind,
                        AVG(temp_f) as avg_temp
                    FROM historical_flights
                    WHERE flight_date IS NOT NULL
                    GROUP BY strftime('%Y-%m', flight_date)
                    ORDER BY month DESC
                """)
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    month, total, cancelled, avg_vis, avg_wind, avg_temp = row
                    cancelled = cancelled or 0
                    rate = (cancelled / total * 100) if total > 0 else 0.0

                    results.append({
                        'month': month,
                        'total_flights': total,
                        'cancelled': cancelled,
                        'cancellation_rate': round(rate, 1),
                        'avg_visibility': round(avg_vis, 1) if avg_vis else None,
                        'avg_wind': round(avg_wind, 1) if avg_wind else None,
                        'avg_temp': round(avg_temp, 1) if avg_temp else None
                    })
                
                return results
        except Exception as e:
            logger.error(f"Failed to get monthly statistics: {e}")
            return []

    def get_history_range(self):
        """
        Returns stats about the historical data range.
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    SELECT 
                        MIN(flight_date), 
                        MAX(flight_date), 
                        COUNT(*) 
                    FROM historical_flights
                """)
                row = cursor.fetchone()
                
                if not row or not row[0]:
                    return {
                        "start_date": None,
                        "end_date": None,
                        "total_flights": 0,
                        "days_covered": 0
                    }
                
                start_date = row[0]
                end_date = row[1]
                total = row[2]
                
                # Calculate days covered
                from datetime import datetime
                try:
                    # Handle potential different date formats
                    # Replace Z with +00:00 for ISO format compliance
                    start_iso = start_date.replace("Z", "+00:00")
                    end_iso = end_date.replace("Z", "+00:00")
                    
                    d1 = datetime.fromisoformat(start_iso)
                    d2 = datetime.fromisoformat(end_iso)
                    
                    # Make both naive to avoid "can't subtract offset-naive and offset-aware" errors
                    if d1.tzinfo:
                        d1 = d1.replace(tzinfo=None)
                    if d2.tzinfo:
                        d2 = d2.replace(tzinfo=None)
                        
                    days = (d2 - d1).days + 1
                except Exception as e:
                    logger.error(f"Date calculation error: {e}")
                    days = 0
                    
                return {
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_flights": total,
                    "days_covered": days
                }
        except Exception as e:
            logger.error(f"Failed to get history range: {e}")
            return {
                "start_date": None,
                "end_date": None,
                "total_flights": 0,
                "days_covered": 0
            }

    # ===== MULTI-AIRPORT WEATHER METHODS =====

    def add_flight_multi_weather(self, data):
        """
        Add flight with comprehensive multi-airport weather data.

        Args:
            data: dict with keys:
                - flight_number: str
                - flight_date: str
                - is_cancelled: bool
                - origin_airport: str (ICAO code)
                - dest_airport: str (ICAO code)
                - puw_weather: dict {visibility_miles, wind_speed_knots, wind_direction, wind_gust_knots,
                                     temp_f, weather_code, precipitation_in, snow_depth_in,
                                     cloud_cover_pct, pressure_mb, humidity_pct, conditions}
                - origin_weather: dict (same structure)
                - dest_weather: dict (same structure)
        """
        check_sql = "SELECT id FROM historical_flights WHERE flight_number = ? AND flight_date = ?"
        insert_sql = """
        INSERT INTO historical_flights (
            flight_number, flight_date, is_cancelled,
            origin_airport, dest_airport,
            puw_visibility_miles, puw_wind_speed_knots, puw_wind_direction, puw_temp_f, puw_weather_code,
            puw_wind_gust_knots, puw_precipitation_in, puw_snow_depth_in,
            puw_cloud_cover_pct, puw_pressure_mb, puw_humidity_pct, puw_conditions,
            origin_visibility_miles, origin_wind_speed_knots, origin_wind_direction, origin_temp_f, origin_weather_code,
            origin_wind_gust_knots, origin_precipitation_in, origin_snow_depth_in,
            origin_cloud_cover_pct, origin_pressure_mb, origin_humidity_pct, origin_conditions,
            dest_visibility_miles, dest_wind_speed_knots, dest_wind_direction, dest_temp_f, dest_weather_code,
            dest_wind_gust_knots, dest_precipitation_in, dest_snow_depth_in,
            dest_cloud_cover_pct, dest_pressure_mb, dest_humidity_pct, dest_conditions,
            visibility_miles, wind_speed_knots, temp_f, snowfall_cm, weather_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            with self._get_conn() as conn:
                # Check for duplicates
                cursor = conn.execute(check_sql, (data.get('flight_number'), data.get('flight_date')))
                if cursor.fetchone():
                    logger.debug(f"Flight {data.get('flight_number')} on {data.get('flight_date')} already exists")
                    return

                # Extract weather data
                puw_weather = data.get('puw_weather', {})
                origin_weather = data.get('origin_weather', {})
                dest_weather = data.get('dest_weather', {})

                # Insert with comprehensive airport weather
                conn.execute(insert_sql, (
                    data.get('flight_number'),
                    data.get('flight_date'),
                    1 if data.get('is_cancelled') else 0,
                    data.get('origin_airport'),
                    data.get('dest_airport'),
                    # PUW weather - core fields
                    puw_weather.get('visibility_miles'),
                    puw_weather.get('wind_speed_knots'),
                    puw_weather.get('wind_direction'),
                    puw_weather.get('temp_f'),
                    puw_weather.get('weather_code'),
                    # PUW weather - comprehensive fields
                    puw_weather.get('wind_gust_knots'),
                    puw_weather.get('precipitation_in'),
                    puw_weather.get('snow_depth_in'),
                    puw_weather.get('cloud_cover_pct'),
                    puw_weather.get('pressure_mb'),
                    puw_weather.get('humidity_pct'),
                    puw_weather.get('conditions'),
                    # Origin weather - core fields
                    origin_weather.get('visibility_miles'),
                    origin_weather.get('wind_speed_knots'),
                    origin_weather.get('wind_direction'),
                    origin_weather.get('temp_f'),
                    origin_weather.get('weather_code'),
                    # Origin weather - comprehensive fields
                    origin_weather.get('wind_gust_knots'),
                    origin_weather.get('precipitation_in'),
                    origin_weather.get('snow_depth_in'),
                    origin_weather.get('cloud_cover_pct'),
                    origin_weather.get('pressure_mb'),
                    origin_weather.get('humidity_pct'),
                    origin_weather.get('conditions'),
                    # Dest weather - core fields
                    dest_weather.get('visibility_miles'),
                    dest_weather.get('wind_speed_knots'),
                    dest_weather.get('wind_direction'),
                    dest_weather.get('temp_f'),
                    dest_weather.get('weather_code'),
                    # Dest weather - comprehensive fields
                    dest_weather.get('wind_gust_knots'),
                    dest_weather.get('precipitation_in'),
                    dest_weather.get('snow_depth_in'),
                    dest_weather.get('cloud_cover_pct'),
                    dest_weather.get('pressure_mb'),
                    dest_weather.get('humidity_pct'),
                    dest_weather.get('conditions'),
                    # Legacy columns (use PUW data for backward compatibility)
                    puw_weather.get('visibility_miles'),
                    puw_weather.get('wind_speed_knots'),
                    puw_weather.get('temp_f'),
                    None,  # snowfall_cm (deprecated, always NULL)
                    puw_weather.get('weather_code')
                ))
                logger.info(f"Added flight {data.get('flight_number')} with comprehensive multi-airport weather")
        except Exception as e:
            logger.error(f"Failed to insert multi-airport flight: {e}", exc_info=True)

    def find_similar_flights_multi_airport(self, puw_weather=None, origin_weather=None, dest_weather=None, flight_type=None):
        """
        Find flights with similar comprehensive weather conditions across multiple airports.
        Uses advanced pattern matching with wind gusts, precipitation, and snow depth.

        Args:
            puw_weather: dict with visibility_miles, wind_speed_knots, wind_gust_knots, temp_f,
                        precipitation_in, snow_depth_in
            origin_weather: dict (same structure)
            dest_weather: dict (same structure)
            flight_type: "arrival" or "departure" (affects which airports are weighted)

        Returns:
            (total_count, cancelled_count)
        """
        sql = "SELECT count(*), sum(is_cancelled) FROM historical_flights WHERE 1=1"
        params = []

        # For arrivals, origin weather matters more
        # For departures, destination weather matters more

        if flight_type == "arrival" and origin_weather:
            # Check origin visibility
            vis = origin_weather.get('visibility_miles')
            if vis is not None and vis < 3.0:
                sql += " AND origin_visibility_miles <= ?"
                params.append(vis + 0.5)

            # Check origin wind (prefer gusts)
            wind_gust = origin_weather.get('wind_gust_knots')
            wind = origin_weather.get('wind_speed_knots')
            effective_wind = wind_gust if wind_gust is not None else wind
            if effective_wind is not None and effective_wind > 20:
                sql += " AND (origin_wind_gust_knots >= ? OR origin_wind_speed_knots >= ?)"
                params.append(effective_wind - 5)
                params.append(effective_wind - 5)

            # Check origin snow depth
            snow = origin_weather.get('snow_depth_in')
            if snow is not None and snow > 1:
                sql += " AND origin_snow_depth_in >= ?"
                params.append(max(0, snow - 2))

            # Check origin precipitation
            precip = origin_weather.get('precipitation_in')
            if precip is not None and precip > 0.1:
                sql += " AND origin_precipitation_in >= ?"
                params.append(max(0, precip - 0.1))

        elif flight_type == "departure" and dest_weather:
            # Check destination visibility
            vis = dest_weather.get('visibility_miles')
            if vis is not None and vis < 3.0:
                sql += " AND dest_visibility_miles <= ?"
                params.append(vis + 0.5)

            # Check destination wind (prefer gusts)
            wind_gust = dest_weather.get('wind_gust_knots')
            wind = dest_weather.get('wind_speed_knots')
            effective_wind = wind_gust if wind_gust is not None else wind
            if effective_wind is not None and effective_wind > 20:
                sql += " AND (dest_wind_gust_knots >= ? OR dest_wind_speed_knots >= ?)"
                params.append(effective_wind - 5)
                params.append(effective_wind - 5)

            # Check destination snow depth
            snow = dest_weather.get('snow_depth_in')
            if snow is not None and snow > 1:
                sql += " AND dest_snow_depth_in >= ?"
                params.append(max(0, snow - 2))

            # Check destination precipitation
            precip = dest_weather.get('precipitation_in')
            if precip is not None and precip > 0.1:
                sql += " AND dest_precipitation_in >= ?"
                params.append(max(0, precip - 0.1))

        # Always check PUW weather for local conditions (comprehensive)
        if puw_weather:
            vis = puw_weather.get('visibility_miles')
            if vis is not None and vis < 3.0:
                sql += " AND puw_visibility_miles <= ?"
                params.append(vis + 0.5)

            wind_gust = puw_weather.get('wind_gust_knots')
            wind = puw_weather.get('wind_speed_knots')
            effective_wind = wind_gust if wind_gust is not None else wind
            if effective_wind is not None and effective_wind > 20:
                sql += " AND (puw_wind_gust_knots >= ? OR puw_wind_speed_knots >= ?)"
                params.append(effective_wind - 5)
                params.append(effective_wind - 5)

            snow = puw_weather.get('snow_depth_in')
            if snow is not None and snow > 1:
                sql += " AND puw_snow_depth_in >= ?"
                params.append(max(0, snow - 2))

            precip = puw_weather.get('precipitation_in')
            if precip is not None and precip > 0.1:
                sql += " AND puw_precipitation_in >= ?"
                params.append(max(0, precip - 0.1))

        try:
            with self._get_conn() as conn:
                cursor = conn.execute(sql, params)
                row = cursor.fetchone()
                if row:
                    total = row[0] or 0
                    cancelled = row[1] or 0
                    return total, cancelled
        except Exception as e:
            logger.error(f"Multi-airport query failed: {e}")

        return 0, 0

    def store_active_flight_with_prediction_multi(self, flight_data, risk_score, puw_weather, origin_weather, dest_weather):
        """
        Store active flight with multi-airport prediction in history_log.

        Args:
            flight_data: flight dict
            risk_score: RiskScore object
            puw_weather: dict
            origin_weather: dict
            dest_weather: dict
        """
        insert_sql = """
        INSERT OR REPLACE INTO history_log (
            flight_id, number, scheduled_time, actual_time, status,
            predicted_risk, predicted_level,
            puw_weather_visibility, puw_weather_wind, puw_weather_temp, puw_weather_code,
            origin_weather_visibility, origin_weather_wind, origin_weather_temp, origin_weather_code,
            dest_weather_visibility, dest_weather_wind, dest_weather_temp, dest_weather_code,
            weather_visibility, weather_wind, weather_temp, weather_code,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            from datetime import datetime, timezone
            with self._get_conn() as conn:
                conn.execute(insert_sql, (
                    flight_data.get('id'),
                    flight_data.get('number'),
                    flight_data.get('scheduled_time'),
                    flight_data.get('actual_time'),
                    flight_data.get('status'),
                    risk_score.score if risk_score else None,
                    risk_score.risk_level if risk_score else None,
                    # PUW weather
                    puw_weather.get('visibility_miles') if puw_weather else None,
                    puw_weather.get('wind_speed_knots') if puw_weather else None,
                    puw_weather.get('temp_f') if puw_weather else None,
                    puw_weather.get('weather_code') if puw_weather else None,
                    # Origin weather
                    origin_weather.get('visibility_miles') if origin_weather else None,
                    origin_weather.get('wind_speed_knots') if origin_weather else None,
                    origin_weather.get('temp_f') if origin_weather else None,
                    origin_weather.get('weather_code') if origin_weather else None,
                    # Dest weather
                    dest_weather.get('visibility_miles') if dest_weather else None,
                    dest_weather.get('wind_speed_knots') if dest_weather else None,
                    dest_weather.get('temp_f') if dest_weather else None,
                    dest_weather.get('weather_code') if dest_weather else None,
                    # Legacy columns (use PUW)
                    puw_weather.get('visibility_miles') if puw_weather else None,
                    puw_weather.get('wind_speed_knots') if puw_weather else None,
                    puw_weather.get('temp_f') if puw_weather else None,
                    puw_weather.get('weather_code') if puw_weather else None,
                    datetime.now(timezone.utc).isoformat()
                ))
        except Exception as e:
            logger.error(f"Failed to store multi-airport prediction: {e}", exc_info=True)

    def get_flight_multi_airport_weather(self, flight_number, flight_date):
        """
        Retrieve multi-airport weather data for a specific historical flight.

        Args:
            flight_number: Flight number (e.g., "AS 2132")
            flight_date: Flight date string (ISO format) or datetime object

        Returns:
            dict with keys 'puw', 'origin', 'dest' containing weather dicts,
            or None if no multi-airport data found
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        # Convert datetime to string if needed, then extract date part (YYYY-MM-DD)
        if hasattr(flight_date, 'strftime'):
            # It's a datetime object
            date_part = flight_date.strftime('%Y-%m-%d')
        elif isinstance(flight_date, str):
            # It's a string
            date_part = flight_date[:10] if len(flight_date) >= 10 else flight_date
        else:
            # Unknown type, return None
            return None

        cursor.execute("""
            SELECT
                puw_visibility_miles, puw_wind_speed_knots, puw_wind_direction, puw_temp_f, puw_weather_code,
                puw_wind_gust_knots, puw_precipitation_in, puw_snow_depth_in,
                puw_cloud_cover_pct, puw_pressure_mb, puw_humidity_pct, puw_conditions,
                origin_visibility_miles, origin_wind_speed_knots, origin_wind_direction, origin_temp_f, origin_weather_code,
                origin_wind_gust_knots, origin_precipitation_in, origin_snow_depth_in,
                origin_cloud_cover_pct, origin_pressure_mb, origin_humidity_pct, origin_conditions,
                dest_visibility_miles, dest_wind_speed_knots, dest_wind_direction, dest_temp_f, dest_weather_code,
                dest_wind_gust_knots, dest_precipitation_in, dest_snow_depth_in,
                dest_cloud_cover_pct, dest_pressure_mb, dest_humidity_pct, dest_conditions,
                origin_airport, dest_airport
            FROM historical_flights
            WHERE flight_number = ? AND substr(flight_date, 1, 10) = ?
            LIMIT 1
        """, (flight_number, date_part))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Unpack row with comprehensive weather fields
        (puw_vis, puw_wind, puw_wind_dir, puw_temp, puw_code,
         puw_gust, puw_precip, puw_snow, puw_cloud, puw_pressure, puw_humidity, puw_conditions,
         origin_vis, origin_wind, origin_wind_dir, origin_temp, origin_code,
         origin_gust, origin_precip, origin_snow, origin_cloud, origin_pressure, origin_humidity, origin_conditions,
         dest_vis, dest_wind, dest_wind_dir, dest_temp, dest_code,
         dest_gust, dest_precip, dest_snow, dest_cloud, dest_pressure, dest_humidity, dest_conditions,
         origin_airport, dest_airport) = row

        # Check if we have any multi-airport data
        has_puw = puw_vis is not None
        has_origin = origin_vis is not None
        has_dest = dest_vis is not None

        if not (has_puw or has_origin or has_dest):
            return None

        result = {}

        if has_puw:
            result['KPUW'] = {
                'visibility_miles': puw_vis,
                'wind_speed_knots': puw_wind,
                'wind_direction': puw_wind_dir,
                'temperature_f': puw_temp,
                'weather_code': puw_code,
                'wind_gust_knots': puw_gust,
                'precipitation_in': puw_precip,
                'snow_depth_in': puw_snow,
                'cloud_cover_pct': puw_cloud,
                'pressure_mb': puw_pressure,
                'humidity_pct': puw_humidity,
                'conditions': puw_conditions
            }

        if has_origin and origin_airport:
            result[origin_airport] = {
                'visibility_miles': origin_vis,
                'wind_speed_knots': origin_wind,
                'wind_direction': origin_wind_dir,
                'temperature_f': origin_temp,
                'weather_code': origin_code,
                'wind_gust_knots': origin_gust,
                'precipitation_in': origin_precip,
                'snow_depth_in': origin_snow,
                'cloud_cover_pct': origin_cloud,
                'pressure_mb': origin_pressure,
                'humidity_pct': origin_humidity,
                'conditions': origin_conditions
            }

        if has_dest and dest_airport:
            result[dest_airport] = {
                'visibility_miles': dest_vis,
                'wind_speed_knots': dest_wind,
                'wind_direction': dest_wind_dir,
                'temperature_f': dest_temp,
                'weather_code': dest_code,
                'wind_gust_knots': dest_gust,
                'precipitation_in': dest_precip,
                'snow_depth_in': dest_snow,
                'cloud_cover_pct': dest_cloud,
                'pressure_mb': dest_pressure,
                'humidity_pct': dest_humidity,
                'conditions': dest_conditions
            }

        return result if result else None
