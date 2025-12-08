import requests
import json
import os
import logging
import time
from datetime import datetime, timedelta, timezone
from .config import Config
from .history_db import HistoryDatabase
from .weather_data import WeatherData
from .prediction_engine import PredictionEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlightDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            if os.path.exists("/data"):
                self.db_path = "/data/flights.db"
            else:
                self.db_path = "flights.db"
        else:
            self.db_path = db_path
        self.history_db = HistoryDatabase()







    def upsert_flights(self, flights):
        """
        Updates existing flights or adds new ones.
        flights: list of flight dicts
        """
        count = 0
        for f in flights:
            self.history_db.upsert_active_flight(f)
            count += 1

        # Update last_updated metadata only if we actually processed flights
        # This prevents failed API calls (returning []) from marking the DB as fresh
        if count > 0:
            self.history_db.set_metadata("last_updated", datetime.now(timezone.utc).isoformat())
        return count

    def get_all_flights(self):
        return self.history_db.get_all_active_flights()

    def get_last_updated(self):
        ts = self.history_db.get_metadata("last_updated")
        if ts:
            return datetime.fromisoformat(ts)
        return None

    def log_flight_outcome(self, flight, weather, risk_score):
        """
        Logs the final outcome of a flight for future analysis.
        """
        self.history_db.log_prediction(flight, weather, risk_score)

    def get_historical_predictions(self):
        """
        Returns a map of flight_id -> {score, level} from the history log.
        """
        return self.history_db.get_historical_predictions()

class AeroDataBoxAPI:
    def __init__(self, api_key=None, airport_code="KPUW"):
        self.api_key = api_key or Config.RAPIDAPI_KEY
        self.airport_code = airport_code
        self.base_url = "https://aerodatabox.p.rapidapi.com/flights/airports/icao"
        self.headers = {
            "x-rapidapi-host": "aerodatabox.p.rapidapi.com",
            "x-rapidapi-key": self.api_key
        }
        self.target_routes = ["KSEA", "KBOI", "SEA", "BOI"]

    def fetch_flights(self, start_dt, end_dt):
        """
        Fetches flights for a specific time window (max 12 hours).
        """
        # Format: YYYY-MM-DDTHH:MM
        
        # AeroDataBox endpoint: /flights/airports/icao/{icao}/{fromLocal}/{toLocal}
        # Note: It expects LOCAL time usually, or we can pass query param?
        # Docs say: "Dates and times are in Local time of the airport"
        # KPUW is US/Pacific.
        
        # We'll use dateutil.
        from dateutil import tz
        to_zone = tz.gettz('America/Los_Angeles')
        from_zone = tz.tzutc()
        
        local_start = start_dt.replace(tzinfo=from_zone).astimezone(to_zone)
        local_end = end_dt.replace(tzinfo=from_zone).astimezone(to_zone)
        
        s_str = local_start.strftime("%Y-%m-%dT%H:%M")
        e_str = local_end.strftime("%Y-%m-%dT%H:%M")
        
        url = f"{self.base_url}/{self.airport_code}/{s_str}/{e_str}"
        
        params = {
            "withLeg": "true",
            "direction": "Both",
            "withCancelled": "true",
            "withCodeshared": "true",
            "withCargo": "false",
            "withPrivate": "false",
            "withLocation": "false"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                return self._parse_response(response.json())
            else:
                logger.error(f"API Error {response.status_code}: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []

    def _parse_response(self, data):
        processed = []
        # AeroDataBox returns { "arrivals": [...], "departures": [...] }
        
        for f_type in ['arrivals', 'departures']:
            for entry in data.get(f_type, []):
                try:
                    # Filter Routes
                    other_airport_code = ""
                    
                    if f_type == 'arrivals':
                        # Origin is the other airport
                        dep_info = entry.get('departure', {})
                        airport_info = dep_info.get('airport', {})
                        other_airport_code = airport_info.get('icao') or airport_info.get('iata')
                    else:
                        # Destination is the other airport
                        arr_info = entry.get('arrival', {})
                        airport_info = arr_info.get('airport', {})
                        other_airport_code = airport_info.get('icao') or airport_info.get('iata')
                    
                    if not other_airport_code or other_airport_code not in self.target_routes:
                        continue

                    # Extract Data
                    number = entry.get('number', 'Unknown')
                    airline = entry.get('airline', {}).get('name', 'Unknown')
                    status = entry.get('status', 'Unknown')
                    
                    # Times
                    time_key = 'arrival' if f_type == 'arrivals' else 'departure'
                    time_obj = entry.get(time_key, {})
                    
                    sched_obj = time_obj.get('scheduledTime', {})
                    actual_obj = time_obj.get('actualTime', {})
                    revised_obj = time_obj.get('revisedTime', {})
                    runway_obj = time_obj.get('runwayTime', {})
                    
                    sched_utc = sched_obj.get('utc')
                    actual_utc = actual_obj.get('utc')
                    revised_utc = revised_obj.get('utc')
                    runway_utc = runway_obj.get('utc')
                    
                    # Aircraft Info
                    aircraft = entry.get('aircraft', {})
                    aircraft_reg = aircraft.get('reg', 'Unknown')
                    aircraft_model = aircraft.get('model', 'Unknown')
                    
                    processed.append({
                        'id': f"{number}_{sched_utc}",
                        'number': number,
                        'airline': airline,
                        'origin': other_airport_code if f_type == 'arrivals' else self.airport_code,
                        'destination': self.airport_code if f_type == 'arrivals' else other_airport_code,
                        'scheduled_time_str': sched_utc,
                        'actual_time_str': actual_utc,
                        'revised_time_str': revised_utc,
                        'runway_time_str': runway_utc,
                        'status': status,
                        'type': 'arrival' if f_type == 'arrivals' else 'departure',
                        'aircraft_reg': aircraft_reg,
                        'aircraft_model': aircraft_model
                    })
                except Exception as e:
                    logger.warning(f"Error parsing flight: {e}")
                    continue
        return processed

class AviationStackAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.aviationstack.com/v1/flights"
        
    def get_flight_status(self, flight_iata):
        """
        Fetch status for a specific flight number.
        Returns the status string (e.g., 'cancelled', 'active', 'landed') or None.
        """
        params = {
            'access_key': self.api_key,
            'flight_iata': flight_iata,
            'limit': 1  # We only need the latest/most relevant
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and data['data']:
                return data['data'][0].get('flight_status')
            return None
        except Exception as e:
            logging.error(f"AviationStack API Error: {e}")
            return None

class FlightData:
    def __init__(self, airport_code="KPUW"):
        self.airport_code = airport_code
        self.api = AeroDataBoxAPI(airport_code=airport_code) 
        self.backup_api = AviationStackAPI(Config.AVIATIONSTACK_KEY)
        self.api = AeroDataBoxAPI(airport_code=airport_code) 
        self.backup_api = AviationStackAPI(Config.AVIATIONSTACK_KEY)
        self.db = FlightDatabase()
        self.history_db = HistoryDatabase()
        
    def get_historical_predictions(self):
        return self.db.get_historical_predictions()
        
    def smart_sync(self, full_sync=False):
        """
        Intelligently fetch data:
        - full_sync=True: Fetches last 12h + next 48h (Deep refresh).
        - full_sync=False: Fetches last 4h + next 8h (Quick refresh for active flights).
        """
        flights = self.db.get_all_flights()
        now = datetime.now(timezone.utc)

        # Cleanup old flights from active_flights table on full sync
        if full_sync:
            self.history_db.cleanup_old_flights(days_back=7)

        # Determine fetch needs
        last_updated = self.db.get_last_updated()
        is_stale = False
        if last_updated:
             # If data is older than 12 hours, consider it stale
             # Ensure last_updated is timezone-aware for comparison
             if last_updated.tzinfo is None:
                 last_updated = last_updated.replace(tzinfo=timezone.utc)
                 
             if (now - last_updated) > timedelta(hours=12):
                 is_stale = True
                 logger.info(f"Data is stale (Last updated: {last_updated}). Forcing full backfill.")

        needs_initial_load = not flights or is_stale

        if needs_initial_load:
            logger.info("Performing initial data fetch (Last 3 days + Next 48h)...")
            # Backfill 3 days (in 12h chunks)
            for i in range(6): # 6 * 12h = 72h = 3 days
                end = now - timedelta(hours=12*i)
                start = end - timedelta(hours=12)
                new_flights = self.api.fetch_flights(start, end)
                self.db.upsert_flights(new_flights)
                time.sleep(1.5) # Rate limit protection
                
            # Fetch Future (Next 48h)
            for i in range(4): # 4 * 12h = 48h
                start = now + timedelta(hours=12*i)
                end = start + timedelta(hours=12)
                new_flights = self.api.fetch_flights(start, end)
                self.db.upsert_flights(new_flights)
                time.sleep(1.5) # Rate limit protection
                
        elif full_sync:
            logger.info("Performing Full Sync (Recent + Future)...")
            # Fetch last 12h (to catch recent landings)
            new_flights = self.api.fetch_flights(now - timedelta(hours=12), now)
            self.db.upsert_flights(new_flights)
            
            # Fetch next 48h
            for i in range(4): # 4 * 12h = 48h
                start = now + timedelta(hours=12*i)
                end = start + timedelta(hours=12)
                new_flights = self.api.fetch_flights(start, end)
                self.db.upsert_flights(new_flights)
                time.sleep(1.5) # Rate limit protection

            # Smart Gap Backfill
            # self.fill_data_gaps(days_back=7) <--- Moved to run on every sync

        else:
            logger.info("Performing Quick Sync (Active Window)...")
            # Fetch -4h to +8h (12h window = 1 API Call)
            # This covers active arrivals/departures and near-term schedule changes
            start = now - timedelta(hours=4)
            end = now + timedelta(hours=8)
            new_flights = self.api.fetch_flights(start, end)
            self.db.upsert_flights(new_flights)
        
        # --- Verification Step ---
        # Check for "Unknown" or "Expected" flights in the past 24h
        self._verify_unknowns(now)

        # --- Smart Gap Backfill ---
        # Check for missing days in the last week and backfill if needed.
        # This runs on every sync (Quick or Full) to ensure robustness.
        self.fill_data_gaps(days_back=7)
        
        return "Sync Complete"

    def fill_data_gaps(self, days_back=7):
        """
        Checks the last N days for missing data (0 flights) and backfills if needed.
        """
        logger.info(f"Checking for data gaps over the last {days_back} days...")
        daily_counts = self.history_db.get_daily_flight_counts(days_back)
        now = datetime.now(timezone.utc)
        
        for i in range(days_back):
            # Check each day
            check_date = now - timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")
            
            # If count is 0 or missing, backfill
            # We assume a healthy day has at least 1 flight.
            if daily_counts.get(date_str, 0) == 0:
                logger.info(f"Gap detected for {date_str}. Backfilling...")
                
                all_new_flights = []

                # Define 24h window for that day (UTC)
                # We want the full UTC day
                start_of_day = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(hours=23, minutes=59)
                
                # Fetch in 12h chunks to be safe with API limits/pagination if any
                # Chunk 1: 00:00 - 12:00
                chunk1_end = start_of_day + timedelta(hours=12)
                flights1 = self.api.fetch_flights(start_of_day, chunk1_end)
                self.db.upsert_flights(flights1)
                all_new_flights.extend(flights1)
                time.sleep(1.5)
                
                # Chunk 2: 12:00 - 23:59
                flights2 = self.api.fetch_flights(chunk1_end, end_of_day)
                self.db.upsert_flights(flights2)
                all_new_flights.extend(flights2)
                time.sleep(1.5)
                
                # Generate retroactive predictions for these flights
                if all_new_flights:
                    self._generate_retroactive_predictions(all_new_flights)

                logger.info(f"Backfill complete for {date_str}")
            else:
                logger.debug(f"Data present for {date_str} ({daily_counts[date_str]} flights). Skipping.")

    def _generate_retroactive_predictions(self, flights):
        """
        Generates risk scores for past flights so the history log is populated.
        """
        try:
            logger.info(f"Generating retroactive predictions for {len(flights)} flights...")
            
            # Initialize engines
            wd = WeatherData()
            pe = PredictionEngine()
            
            # 1. Get historical weather for these flights
            # We need to convert the raw flight dicts (which have string times) 
            # into a format WeatherData expects (dicts with datetime objects)
            
            # Helper to parse time for weather lookup
            def parse_time(t_str):
                if not t_str: return None
                return datetime.fromisoformat(t_str.replace("Z", "+00:00"))

            flights_with_dt = []
            for f in flights:
                f_copy = f.copy()
                f_copy['scheduled_time'] = parse_time(f.get('scheduled_time_str'))
                flights_with_dt.append(f_copy)

            weather_map = wd.get_weather_for_flights(flights_with_dt)
            
            # 2. Calculate risk for each flight
            count = 0
            for i, f in enumerate(flights):
                f_dt = flights_with_dt[i]
                sched_dt = f_dt.get('scheduled_time')
                
                if not sched_dt:
                    continue
                    
                # Lookup weather (same logic as api.py)
                lookup_time = sched_dt.replace(minute=0, second=0, microsecond=0)
                if sched_dt.minute >= 30:
                    lookup_time = lookup_time + timedelta(hours=1)
                
                # Try exact match or offset
                w_cond = weather_map.get(lookup_time.replace(tzinfo=None)) or weather_map.get(lookup_time)
                
                if w_cond:
                    # Calculate Risk
                    risk_score = pe.calculate_flight_risk(f, w_cond)
                    
                    # Log it
                    self.history_db.log_prediction(f, w_cond, risk_score)
                    count += 1
            
            logger.info(f"Generated {count} retroactive predictions.")
            
        except Exception as e:
            logger.error(f"Failed to generate retroactive predictions: {e}")

    def _verify_unknowns(self, now):
        """
        Check for flights with ambiguous status in the past and verify with backup API.
        """
        flights = self.db.get_all_flights()
        updates_made = False
        
        candidates = []
        for f in flights:
            # Parse time
            # Raw DB uses 'scheduled_time_str'
            sched_str = f.get('scheduled_time_str')
            if not sched_str:
                continue
                
            try:
                sched_time = datetime.fromisoformat(sched_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            
            # Ensure timezone aware
            if sched_time.tzinfo is None:
                sched_time = sched_time.replace(tzinfo=timezone.utc)
                
            if sched_time < now and sched_time > now - timedelta(hours=24):
                if f.get('status', '').lower() in ['unknown', 'expected']:
                    candidates.append(f)
        
        if candidates:
            logger.info(f"Verifying {len(candidates)} uncertain flights with AviationStack...")
            for f in candidates:
                # Construct IATA flight number (e.g. AS2132)
                flight_iata = f['number'].replace(" ", "")
                
                real_status = self.backup_api.get_flight_status(flight_iata)
                if real_status:
                    logger.info(f"Updated {flight_iata}: {f['status']} -> {real_status}")
                    f['status'] = real_status.capitalize()
                    updates_made = True
                    # Re-upsert the flight with updated status
                    self.db.upsert_flights([f])
                else:
                    logging.warning(f"Could not verify {flight_iata}")

    def get_flights(self, days_back=7, hours_forward=48):
        """
        Returns flights from local DB, filtered by range.
        """
        raw_flights = self.db.get_all_flights()
        
        # Convert strings back to datetime objects for the app
        processed = []
        for f in raw_flights:
            f_copy = f.copy()
            if f.get('scheduled_time_str'):
                f_copy['scheduled_time'] = datetime.fromisoformat(f['scheduled_time_str'].replace("Z", "+00:00"))
            else:
                f_copy['scheduled_time'] = None
                
            if f.get('actual_time_str'):
                f_copy['actual_time'] = datetime.fromisoformat(f['actual_time_str'].replace("Z", "+00:00"))
            else:
                f_copy['actual_time'] = None
                
            if f.get('revised_time_str'):
                f_copy['revised_time'] = datetime.fromisoformat(f['revised_time_str'].replace("Z", "+00:00"))
            else:
                f_copy['revised_time'] = None

            if f.get('runway_time_str'):
                f_copy['runway_time'] = datetime.fromisoformat(f['runway_time_str'].replace("Z", "+00:00"))
            else:
                f_copy['runway_time'] = None
            
            processed.append(f_copy)
            
        # Filter
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=days_back)
        end_time = now + timedelta(hours=hours_forward)
        
        filtered = []
        for f in processed:
            t = f.get('scheduled_time')
            if t and start_time <= t <= end_time:
                filtered.append(f)
                
        return filtered
        
    def get_last_updated_str(self):
        dt = self.db.get_last_updated()
        if dt:
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        return "Never"

    def log_flight_outcome(self, flight, weather, risk_score):
        # 1. Log to JSON (Legacy/Backup)
        self.db.log_flight_outcome(flight, weather, risk_score)
        
        # 2. Log to SQLite (Active History)
        # Map data format
        try:
            # Parse date
            sched_str = flight.get('scheduled_time_str')
            flight_date = None
            if sched_str:
                # ISO string to YYYY-MM-DD
                flight_date = sched_str.split('T')[0]
                
            # Weather extraction
            vis = None
            wind = None
            temp = None
            
            # Handle dict or object
            w_dict = weather.dict() if hasattr(weather, 'dict') else weather
            if w_dict:
                vis = w_dict.get('visibility_miles')
                wind = w_dict.get('wind_speed_knots')
                temp = w_dict.get('temperature_f')
            
            data = {
                'flight_number': flight.get('number'),
                'flight_date': flight_date,
                'is_cancelled': flight.get('status', '').lower() in ['cancelled', 'canceled'],
                'visibility_miles': vis,
                'wind_speed_knots': wind,
                'temp_f': temp,
                'snowfall_cm': 0.0, # Not captured in live weather yet
                'weather_code': 0 # Not captured
            }
            
            self.history_db.add_flight(data)
            logger.info(f"Logged flight {flight.get('number')} to history.db")
            
        except Exception as e:
            logger.error(f"Failed to log to history.db: {e}")

if __name__ == "__main__":
    # Test
    fd = FlightData()
    print("Updating data...")
    status_message = fd.smart_sync()
    print(status_message)
    
    flights = fd.get_flights()
    print(f"Total flights in DB: {len(flights)}")
    print(f"Last updated: {fd.get_last_updated_str()}")
