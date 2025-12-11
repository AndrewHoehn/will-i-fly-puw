from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
import os
from datetime import datetime, timezone, timedelta
from dateutil import tz

# Import our existing logic
# Note: We assume these files are in the same directory as api.py
from .flight_data import FlightData
from .weather_data import WeatherData
from .faa_data import FAAStatusAPI
from .prediction_engine import PredictionEngine, RiskScore

# Configure Logging
log_handlers = [logging.StreamHandler()]
if os.path.exists("/data"):
    log_handlers.append(logging.FileHandler("/data/app.log"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger("kpuw_api")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.background import BackgroundScheduler
import os

# ... (Imports)

app = FastAPI(title="KPUW Flight Tracker API")



# CORS - Allow frontend to access (Keep for dev, but less needed for static serving)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Data Managers
fd = FlightData()
wd = WeatherData()
faa = FAAStatusAPI()
pe = PredictionEngine()

# Event-Driven Cache for Dashboard Data
dashboard_cache = {
    "data": None,
    "valid": False
}

monthly_stats_cache = {
    "data": None,
    "valid": False
}

bts_stats_cache = {
    "data": None,
    "valid": False
}

def invalidate_dashboard_cache():
    """Invalidate dashboard cache when flight data changes"""
    dashboard_cache["valid"] = False
    monthly_stats_cache["valid"] = False
    logger.info("Dashboard cache invalidated")

def sync_and_invalidate(full_sync=False):
    """Wrapper for smart_sync that invalidates cache after sync"""
    fd.smart_sync(full_sync=full_sync)
    invalidate_dashboard_cache()

# Scheduler Setup
scheduler = BackgroundScheduler()

# Quick Sync every 45 minutes (Active Window: -4h to +8h)
# Uses 1 API call per run -> ~32 calls/day
scheduler.add_job(lambda: sync_and_invalidate(full_sync=False), 'interval', minutes=45)

# Full Sync every 8 hours (Deep Refresh: -12h to +48h)
# Uses 1 API call per run -> ~3 calls/day
scheduler.add_job(lambda: sync_and_invalidate(full_sync=True), 'interval', hours=8)

# Database Backup every 24 hours
if os.getenv("BACKUP_ENABLED", "true").lower() == "true":
    from .backup_manager import scheduled_backup
    backup_interval = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
    scheduler.add_job(scheduled_backup, 'interval', hours=backup_interval)
    logger.info(f"Automated backups enabled (every {backup_interval} hours)")

scheduler.start()

@app.on_event("startup")
def startup_event():
    """
    Run on application startup.
    Checks if the database is empty and performs an initial sync if needed.
    """
    logger.info("Application startup: Checking for initial data...")
    try:
        # smart_sync has built-in logic: if DB is empty, it does a full backfill/forward fill.
        # We force full_sync=True on startup to ensure we have the next 48h of data immediately.
        sync_and_invalidate(full_sync=True)
    except Exception as e:
        logger.error(f"Failed to perform initial sync on startup: {e}")

# --- Models ---
class Flight(BaseModel):
    id: str
    number: str
    airline: str
    origin: str
    destination: str
    status: str
    scheduled_time: str # ISO string
    actual_time: Optional[str] = None
    type: str # 'arrival' or 'departure'
    aircraft_reg: Optional[str] = None
    aircraft_model: Optional[str] = None
    local_time_str: Optional[str] = None # Helper for frontend
    
class WeatherInfo(BaseModel):
    visibility_miles: Optional[float] = None
    wind_speed_knots: Optional[float] = None
    temperature_f: Optional[float] = None
    is_adverse: bool = False
    description: str = ""

class FlightResponse(Flight):
    weather: Optional[WeatherInfo] = None
    inbound_alert: Optional[str] = None
    risk_score: Optional[dict] = None # {score, factors, level}
    prediction_grade: Optional[str] = None # "Nailed It", "Miss", "Smooth", "False Alarm"
    multi_airport_weather: Optional[dict] = None # {KPUW: {...}, KSEA: {...}, KBOI: {...}}

class Stats(BaseModel):
    reliability_today: dict # { "cancelled": int, "total": int }
    reliability_yesterday: dict # { "cancelled": int, "total": int }
    reliability_7_days: dict # { "rate": float, "cancelled": int, "total": int }
    reliability_30_days: dict # { "rate": float, "cancelled": int, "total": int }
    weather_risk_future: dict # { "at_risk": int, "total": int }

class DataFreshness(BaseModel):
    last_flight_sync: str # ISO timestamp
    last_weather_sync: str # ISO timestamp or "Just now"
    flight_data_age_minutes: int
    weather_data_age_minutes: int
    is_stale: bool # True if data is > 60 minutes old

class DashboardData(BaseModel):
    historical: List[FlightResponse]
    future: List[FlightResponse]
    last_updated: str
    faa_status: dict
    stats: Stats
    weather_forecast: List[dict] # Simple daily forecast
    data_freshness: DataFreshness
    history_range: Optional[dict] = None # {start_date, end_date, total_flights, days_covered}

# --- Helpers ---
def process_flights():
    """
    Fetches flights from DB, adds weather, and processes them for the frontend.
    """
    flights = fd.get_flights(days_back=7, hours_forward=48)
    weather_map = wd.get_weather_for_flights(flights)
    
    # Timezone setup
    to_zone = tz.gettz('America/Los_Angeles')
    from_zone = tz.tzutc()
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(to_zone)
    yesterday_local = now_local - timedelta(days=1)
    
    # Inbound Linking Map
    aircraft_map = {}
    for f in flights:
        reg = f.get('aircraft_reg')
        if reg and reg != 'Unknown':
            if reg not in aircraft_map:
                aircraft_map[reg] = []
            aircraft_map[reg].append(f)
    for reg in aircraft_map:
        aircraft_map[reg].sort(key=lambda x: x['scheduled_time']) # Assumes datetime obj in dict

    processed_historical = []
    processed_future = []
    
    tomorrow_end = (now_local + timedelta(days=1)).replace(hour=23, minute=59, second=59) + timedelta(hours=1)

    # Stats Counters
    today_cancelled = 0
    today_total = 0
    yesterday_cancelled = 0
    yesterday_total = 0
    future_risk = 0
    future_total = 0

    # Load Historical Predictions
    hist_preds = fd.get_historical_predictions()

    for f in flights:
        # Time conversion
        sched_dt = f['scheduled_time']
        if sched_dt.tzinfo is None:
            sched_dt = sched_dt.replace(tzinfo=from_zone)
        local_dt = sched_dt.astimezone(to_zone)
        
        # Format for JSON
        f_out = f.copy()
        f_out['scheduled_time'] = sched_dt.isoformat()
        # 12-hour format (e.g. "02:30 PM")
        f_out['local_time_str'] = local_dt.strftime("%I:%M %p")
        if f.get('actual_time'):
             f_out['actual_time'] = f['actual_time'].replace(tzinfo=from_zone).isoformat()
        
        # Weather
        # Lookup logic (naive/aware handling)
        lookup_time = sched_dt.replace(minute=0, second=0, microsecond=0)
        if sched_dt.minute >= 30:
            lookup_time = lookup_time + timedelta(hours=1)
        
        w_cond = weather_map.get(lookup_time.replace(tzinfo=None)) or weather_map.get(lookup_time)
        w_info = None
        is_adverse_weather = False
        if w_cond:
            flags = wd.check_conditions(w_cond)
            is_adverse_weather = len(flags) > 0
            desc = []
            if w_cond.get('temperature_f') is not None:
                desc.append(f"{w_cond['temperature_f']:.0f}°F")
            if w_cond.get('visibility_miles') is not None:
                desc.append(f"Vis: {w_cond['visibility_miles']:.1f}mi")
            if w_cond.get('wind_speed_knots') is not None:
                desc.append(f"Wind: {w_cond['wind_speed_knots']:.0f}kn")
            
            w_info = WeatherInfo(
                visibility_miles=w_cond.get('visibility_miles'),
                wind_speed_knots=w_cond.get('wind_speed_knots'),
                temperature_f=w_cond.get('temperature_f'),
                is_adverse=is_adverse_weather,
                description=", ".join(desc)
            )
        
        # Inbound Alert (Future only)
        inbound_msg = None
        if local_dt > now_local and f['type'] == 'departure':
             reg = f.get('aircraft_reg')
             if reg and reg != 'Unknown' and f.get('id'):
                 plane_flights = aircraft_map.get(reg, [])
                 try:
                     # Find index by ID
                     # Note: f is the raw dict, plane_flights has raw dicts
                     idx = next(i for i, x in enumerate(plane_flights) if x.get('id') == f['id'])
                     if idx > 0:
                         inbound = plane_flights[idx-1]
                         in_stat = inbound['status'].lower()
                         if in_stat in ['cancelled', 'canceled']:
                             inbound_msg = f"Inbound {inbound['number']} Cancelled"
                         elif in_stat not in ['active', 'landed', 'scheduled', 'expected']:
                             inbound_msg = f"Inbound: {inbound['status']}"
                 except StopIteration:
                     pass

        # Construct Response Object
        status_raw = f.get('status', 'Unknown')
        status_display = status_raw
        
        # Normalize status for display and logic
        if local_dt > now_local:
            # FUTURE FLIGHTS
            # "Unknown" usually means "Scheduled" in our API source
            if status_raw.lower() == 'unknown':
                status_display = 'Scheduled'
        else:
            # PAST FLIGHTS
            # If a flight is in the past but still "Expected", "Scheduled", or "Unknown",
            # it implies the API stopped tracking it. We assume it completed normally.
            if status_raw.lower() in ['expected', 'scheduled', 'unknown', 'active']:
                if f['type'] == 'arrival':
                    status_display = 'Landed'
                else:
                    status_display = 'Departed'
        
        effective_status = status_display.lower()
        f_out['status'] = status_display 

        # Prediction Engine
        risk_obj = None
        prediction_grade = None # For Scorecard
        multi_airport_weather = None

        # Extract multi-airport weather from weather_map (for both future AND historical)
        # Helper to ensure numeric values
        def ensure_numeric_weather(weather_dict):
            if not weather_dict:
                return {}
            w = weather_dict.copy()
            numeric_fields = ['visibility_miles', 'wind_speed_knots', 'wind_direction', 'temperature_f',
                            'wind_gust_knots', 'precipitation_in', 'snow_depth_in',
                            'cloud_cover_pct', 'pressure_mb', 'humidity_pct', 'weather_code']
            for field in numeric_fields:
                if field in w and w[field] is not None:
                    try:
                        # Convert to float if it's a string
                        if isinstance(w[field], str):
                            w[field] = float(w[field])
                    except (ValueError, TypeError):
                        w[field] = None
            return w

        puw_weather = ensure_numeric_weather(w_cond) if w_cond else {}
        origin_weather = {}
        dest_weather = {}

        # Get weather from airports dict if available
        if w_cond and 'airports' in w_cond:
            airports_weather = w_cond['airports']
            puw_weather = ensure_numeric_weather(airports_weather.get('KPUW', w_cond))

            # Get origin/destination weather
            origin_code = f_out.get('origin')
            dest_code = f_out.get('destination')

            if origin_code and origin_code in airports_weather:
                origin_weather = ensure_numeric_weather(airports_weather[origin_code])

            if dest_code and dest_code in airports_weather:
                dest_weather = ensure_numeric_weather(airports_weather[dest_code])

        if local_dt > now_local:
            # Future: Calculate Fresh Risk with Multi-Airport Weather
            # Use multi-airport risk calculation
            risk_obj = pe.calculate_risk_multi_airport(f_out, puw_weather, origin_weather, dest_weather)

            # Build multi-airport weather dict for frontend
            multi_airport_weather = {}
            if puw_weather:
                multi_airport_weather['KPUW'] = {
                    'visibility_miles': puw_weather.get('visibility_miles'),
                    'wind_speed_knots': puw_weather.get('wind_speed_knots'),
                    'wind_direction': puw_weather.get('wind_direction'),
                    'temperature_f': puw_weather.get('temperature_f'),
                    'weather_code': puw_weather.get('weather_code'),
                    'airport_name': 'Pullman-Moscow Regional'
                }
            if origin_weather and f_out.get('origin'):
                origin_code = f_out['origin']
                airport_name = {'KSEA': 'Seattle-Tacoma', 'KBOI': 'Boise'}.get(origin_code, origin_code)
                multi_airport_weather[origin_code] = {
                    'visibility_miles': origin_weather.get('visibility_miles'),
                    'wind_speed_knots': origin_weather.get('wind_speed_knots'),
                    'wind_direction': origin_weather.get('wind_direction'),
                    'temperature_f': origin_weather.get('temperature_f'),
                    'weather_code': origin_weather.get('weather_code'),
                    'airport_name': airport_name
                }
            if dest_weather and f_out.get('destination'):
                dest_code = f_out['destination']
                airport_name = {'KSEA': 'Seattle-Tacoma', 'KBOI': 'Boise'}.get(dest_code, dest_code)
                multi_airport_weather[dest_code] = {
                    'visibility_miles': dest_weather.get('visibility_miles'),
                    'wind_speed_knots': dest_weather.get('wind_speed_knots'),
                    'wind_direction': dest_weather.get('wind_direction'),
                    'temperature_f': dest_weather.get('temperature_f'),
                    'weather_code': dest_weather.get('weather_code'),
                    'airport_name': airport_name
                }
        else:
            # Historical: Retrieve Logged Prediction
            # If not found, we could re-calculate, but that's "cheating".
            # Let's only show scorecard if we actually predicted it.
            flight_id = f.get('id')
            logged = hist_preds.get(flight_id) if flight_id else None
            if logged and logged.get('score') is not None:
                # Reconstruct a partial risk object for display
                risk_obj = RiskScore(logged['score'], [], logged['level'], breakdown={}, detailed_factors=[])

                # Grade the Prediction
                # High Risk (>= 70) + Cancelled = Nailed It
                # Low Risk (< 40) + Landed = Smooth Sailing
                # High Risk + Landed = False Alarm
                # Low Risk + Cancelled = Miss

                score = logged['score']
                is_cancelled = effective_status in ['cancelled', 'canceled']
                is_landed = effective_status in ['landed', 'arrived', 'departed']

                if is_cancelled:
                    if score >= 70: prediction_grade = "Nailed It"
                    elif score < 40: prediction_grade = "Miss"
                    else: prediction_grade = "Neutral" # Medium risk is ambiguous
                elif is_landed:
                    if score < 40: prediction_grade = "Smooth"
                    elif score >= 70: prediction_grade = "False Alarm"
                    else: prediction_grade = "Neutral"

            # Fetch multi-airport weather from historical database
            historical_weather = fd.history_db.get_flight_multi_airport_weather(
                f.get('number'),
                f.get('scheduled_time')
            )

            if historical_weather:
                # Build multi-airport weather dict for frontend
                multi_airport_weather = {}

                if 'KPUW' in historical_weather:
                    multi_airport_weather['KPUW'] = {
                        **historical_weather['KPUW'],
                        'airport_name': 'Pullman-Moscow Regional'
                    }

                # Add origin airport if exists
                origin_code = f.get('origin')
                if origin_code and origin_code in historical_weather:
                    airport_name = {'KSEA': 'Seattle-Tacoma', 'KBOI': 'Boise'}.get(origin_code, origin_code)
                    multi_airport_weather[origin_code] = {
                        **historical_weather[origin_code],
                        'airport_name': airport_name
                    }

                # Add destination airport if exists
                dest_code = f.get('destination')
                if dest_code and dest_code in historical_weather:
                    airport_name = {'KSEA': 'Seattle-Tacoma', 'KBOI': 'Boise'}.get(dest_code, dest_code)
                    multi_airport_weather[dest_code] = {
                        **historical_weather[dest_code],
                        'airport_name': airport_name
                    }

        resp_item = FlightResponse(
            **f_out,
            weather=w_info,
            inbound_alert=inbound_msg,
            risk_score=risk_obj.to_dict() if risk_obj else None,
            prediction_grade=prediction_grade,
            multi_airport_weather=multi_airport_weather
        )

        if local_dt <= now_local:
            processed_historical.append(resp_item)
            # Stats: Today's Reliability
            if local_dt.date() == now_local.date():
                today_total += 1
                if status_display.lower() in ['cancelled', 'canceled']:
                    today_cancelled += 1
            # Stats: Yesterday's Reliability
            elif local_dt.date() == yesterday_local.date():
                yesterday_total += 1
                if status_display.lower() in ['cancelled', 'canceled']:
                    yesterday_cancelled += 1

            # Log History with Multi-Airport Weather (Self-Grading)
            # Calculate risk using multi-airport weather (same as future flights)
            risk_for_log = pe.calculate_risk_multi_airport(f_out, puw_weather, origin_weather, dest_weather)

            # Log prediction to history_log table (for scorecard)
            fd.history_db.log_prediction(f_out, w_cond, risk_for_log)

            # Log multi-airport weather to historical_flights table
            # This ensures Recent History can display multi-airport weather
            flight_date_str = f_out.get('scheduled_time')[:10] if f_out.get('scheduled_time') else None
            if flight_date_str and (puw_weather or origin_weather or dest_weather):
                # Convert weather dicts to match expected format (temp_f instead of temperature_f)
                # Also ensure all numeric values are actually numeric (not strings)
                def prepare_weather(weather_dict):
                    if not weather_dict:
                        return {}
                    w = weather_dict.copy()
                    if 'temperature_f' in w:
                        w['temp_f'] = w.pop('temperature_f')

                    # Ensure numeric fields are floats, not strings
                    numeric_fields = ['visibility_miles', 'wind_speed_knots', 'wind_direction', 'temp_f',
                                    'wind_gust_knots', 'precipitation_in', 'snow_depth_in',
                                    'cloud_cover_pct', 'pressure_mb', 'humidity_pct', 'weather_code']
                    for field in numeric_fields:
                        if field in w and w[field] is not None:
                            try:
                                w[field] = float(w[field]) if not isinstance(w[field], (int, float)) else w[field]
                            except (ValueError, TypeError):
                                w[field] = None
                    return w

                fd.history_db.add_flight_multi_weather({
                    'flight_number': f_out.get('number'),
                    'flight_date': flight_date_str,
                    'is_cancelled': effective_status in ['cancelled', 'canceled'],
                    'origin_airport': f_out.get('origin'),
                    'dest_airport': f_out.get('destination'),
                    'puw_weather': prepare_weather(puw_weather),
                    'origin_weather': prepare_weather(origin_weather),
                    'dest_weather': prepare_weather(dest_weather)
                })
                    
        elif local_dt <= tomorrow_end:
            processed_future.append(resp_item)
            # Stats: Future Risk
            future_total += 1
            if is_adverse_weather or inbound_msg:
                future_risk += 1
            
    # Sort
    processed_historical.sort(key=lambda x: x.scheduled_time, reverse=True)
    processed_future.sort(key=lambda x: x.scheduled_time)

    # 7-Day and 30-Day Stats
    stats_7 = fd.history_db.get_recent_stats(7)
    stats_30 = fd.history_db.get_recent_stats(30)

    stats = Stats(
        reliability_today={"cancelled": today_cancelled, "total": today_total},
        reliability_yesterday={"cancelled": yesterday_cancelled, "total": yesterday_total},
        reliability_7_days=stats_7,
        reliability_30_days=stats_30,
        weather_risk_future={"at_risk": future_risk, "total": future_total}
    )
    
    # Simple Forecast (Next 3 Days)
    # We can extract this from weather_map or just use a few points
    # Let's just grab noon weather for next 3 days
    forecast = []
    for i in range(3):
        target = now_local + timedelta(days=i)
        target = target.replace(hour=12, minute=0, second=0, microsecond=0)
        # Convert to UTC for lookup
        target_utc = target.astimezone(timezone.utc).replace(tzinfo=None)
        
        # Find closest weather point
        w = weather_map.get(target_utc)
        if w:
            forecast.append({
                "day": target.strftime("%a"), # Mon, Tue
                "temp": w.get('temperature_f'),
                "desc": "Snow" if w.get('temperature_f') is not None and w.get('temperature_f') < 32 and w.get('precipitation_probability', 0) > 30 else "Cloudy" # Simple heuristic
            })
            
    return processed_historical, processed_future, stats, forecast

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring services like UptimeRobot.
    Returns 200 OK if all critical services are operational.
    """
    try:
        checks = {}

        # Check 1: Database is accessible
        try:
            stats = fd.history_db.get_recent_stats(1)
            checks["database"] = "ok" if stats else "warning"
        except Exception as e:
            logger.error(f"Health check - database error: {e}")
            checks["database"] = "error"

        # Check 2: We have flight data
        try:
            flights = fd.get_flights()
            checks["flights"] = "ok" if flights and len(flights) > 0 else "warning"
        except Exception as e:
            logger.error(f"Health check - flights error: {e}")
            checks["flights"] = "error"

        # Check 3: Weather API is accessible
        try:
            # Check if we've successfully fetched weather recently (within last hour)
            if wd.last_weather_fetch:
                time_since_fetch = datetime.now(timezone.utc) - wd.last_weather_fetch
                if time_since_fetch < timedelta(hours=1):
                    checks["weather"] = "ok"
                else:
                    checks["weather"] = "warning"
            else:
                checks["weather"] = "warning"
        except Exception as e:
            logger.error(f"Health check - weather error: {e}")
            checks["weather"] = "warning"

        # Overall status
        has_errors = any(v == "error" for v in checks.values())
        status = "degraded" if has_errors else "healthy"

        response = {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks
        }

        # Return 503 if any critical service has errors
        if has_errors:
            raise HTTPException(status_code=503, detail=response)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
        )

@app.get("/api/dashboard", response_model=DashboardData)
async def get_dashboard_data():
    # Check cache first
    if dashboard_cache["valid"] and dashboard_cache["data"]:
        logger.debug("Serving dashboard from cache")
        return dashboard_cache["data"]

    logger.info("Computing fresh dashboard data")

    try:
        hist, fut, stats, forecast = process_flights()

        # FAA Status
        sea = faa.get_airport_status("SEA")
        boi = faa.get_airport_status("BOI")

        # Data Freshness Calculation
        now = datetime.now(timezone.utc)

        # Flight data freshness
        last_flight_sync = fd.db.get_last_updated()
        if last_flight_sync:
            flight_age_minutes = int((now - last_flight_sync).total_seconds() / 60)
            last_flight_sync_str = last_flight_sync.isoformat()
        else:
            flight_age_minutes = 9999
            last_flight_sync_str = "Never"

        # Weather data freshness
        last_weather_sync = wd.get_last_weather_sync()
        if last_weather_sync:
            weather_age_minutes = int((now - last_weather_sync).total_seconds() / 60)
            last_weather_sync_str = last_weather_sync.isoformat()
        else:
            weather_age_minutes = 9999
            last_weather_sync_str = "Never"

        # Data is considered stale if either flight or weather data is > 60 minutes old
        is_stale = flight_age_minutes > 60 or weather_age_minutes > 60

        freshness = DataFreshness(
            last_flight_sync=last_flight_sync_str,
            last_weather_sync=last_weather_sync_str,
            flight_data_age_minutes=flight_age_minutes,
            weather_data_age_minutes=weather_age_minutes,
            is_stale=is_stale
        )

        # Get last updated as ISO timestamp for frontend
        last_updated_dt = fd.db.get_last_updated()
        last_updated_iso = last_updated_dt.isoformat() if last_updated_dt else None

        # Get History Range
        history_range = fd.history_db.get_history_range()

        dashboard_data = DashboardData(
            historical=hist,
            future=fut,
            last_updated=last_updated_iso or "Never",
            faa_status={"SEA": sea, "BOI": boi},
            stats=stats,
            weather_forecast=forecast,
            data_freshness=freshness,
            history_range=history_range
        )

        # Cache the result
        dashboard_cache["data"] = dashboard_data
        dashboard_cache["valid"] = True
        logger.info("Dashboard data cached")

        return dashboard_data
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh")
async def refresh_data():
    """Manual refresh endpoint - invalidates cache and forces full sync"""
    try:
        sync_and_invalidate(full_sync=True)
        return {"message": "Data refreshed successfully and cache invalidated"}
    except Exception as e:
        logger.error(f"Error refreshing data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monthly-stats")
async def get_monthly_statistics():
    """
    Returns monthly statistics from historical flight data.
    """
    # Check cache first
    if monthly_stats_cache["valid"] and monthly_stats_cache["data"]:
        logger.debug("Serving monthly stats from cache")
        return monthly_stats_cache["data"]

    logger.info("Computing fresh monthly statistics")

    try:
        try:
            from .history_db import HistoryDatabase
        except ImportError:
            from history_db import HistoryDatabase

        history_db = HistoryDatabase()
        stats = history_db.get_monthly_statistics()

        result = {"monthly_stats": stats}

        # Cache the result
        monthly_stats_cache["data"] = result
        monthly_stats_cache["valid"] = True
        logger.info("Monthly stats cached")

        return result
    except Exception as e:
        logger.error(f"Error fetching monthly statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bts-monthly-stats")
async def get_bts_monthly_statistics():
    """
    Returns BTS (Bureau of Transportation Statistics) monthly statistics for KPUW.
    Includes delay cause breakdown and historical cancellation rates (2020-2025).
    BTS data is static, so cached indefinitely until server restart.
    """
    # Check cache first - BTS data never changes, so cache forever
    if bts_stats_cache["valid"] and bts_stats_cache["data"]:
        logger.debug("Serving BTS stats from cache")
        return bts_stats_cache["data"]

    logger.info("Loading BTS statistics (first time)")

    try:
        try:
            from .ingest_bts_data import BTSDataIngester
        except ImportError:
            from ingest_bts_data import BTSDataIngester

        ingester = BTSDataIngester()
        stats = ingester.get_monthly_stats()
        overall_breakdown = ingester.get_delay_cause_breakdown()

        result = {
            "bts_stats": stats,
            "overall_delay_breakdown": overall_breakdown,
            "data_range": {
                "start": f"{stats[-1]['year']}-{stats[-1]['month']:02d}" if stats else None,
                "end": f"{stats[0]['year']}-{stats[0]['month']:02d}" if stats else None,
                "total_months": len(stats)
            }
        }

        # Cache the result (BTS data is static)
        bts_stats_cache["data"] = result
        bts_stats_cache["valid"] = True
        logger.info("BTS stats cached (static data)")

        return result
    except Exception as e:
        logger.error(f"Error fetching BTS statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
async def get_admin_stats():
    """
    Admin endpoint - Returns comprehensive database statistics and health metrics.
    Easter egg endpoint for database inspection.
    """
    try:
        conn = fd.history_db._get_conn()
        cursor = conn.cursor()

        # Total flights
        cursor.execute("SELECT COUNT(*) FROM historical_flights")
        total_flights = cursor.fetchone()[0]

        # Flights with complete multi-airport weather
        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE puw_visibility_miles IS NOT NULL
            AND origin_visibility_miles IS NOT NULL
            AND dest_visibility_miles IS NOT NULL
        """)
        complete_weather = cursor.fetchone()[0]

        # Flights missing weather data
        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE puw_visibility_miles IS NULL
            OR origin_visibility_miles IS NULL
            OR dest_visibility_miles IS NULL
        """)
        missing_weather = cursor.fetchone()[0]

        # Cancelled vs completed flights
        cursor.execute("SELECT COUNT(*) FROM historical_flights WHERE is_cancelled = 1")
        cancelled = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM historical_flights WHERE is_cancelled = 0")
        completed = cursor.fetchone()[0]

        # Date range
        cursor.execute("SELECT MIN(flight_date), MAX(flight_date) FROM historical_flights")
        date_range = cursor.fetchone()

        # Weather condition breakdown (flights with multi-airport weather)
        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE puw_visibility_miles IS NOT NULL
            AND puw_visibility_miles < 1.0
        """)
        low_vis_puw = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE puw_visibility_miles IS NOT NULL
            AND puw_wind_speed_knots > 30
        """)
        high_wind_puw = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE puw_temp_f IS NOT NULL
            AND puw_temp_f < 32
        """)
        freezing_puw = cursor.fetchone()[0]

        # Origin airport weather breakdown
        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE origin_visibility_miles IS NOT NULL
            AND origin_visibility_miles < 1.0
        """)
        low_vis_origin = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE origin_wind_speed_knots IS NOT NULL
            AND origin_wind_speed_knots > 30
        """)
        high_wind_origin = cursor.fetchone()[0]

        # Destination airport weather breakdown
        cursor.execute("""
            SELECT COUNT(*) FROM historical_flights
            WHERE dest_visibility_miles IS NOT NULL
            AND dest_visibility_miles < 1.0
        """)
        low_vis_dest = cursor.fetchone()[0]

        # Flights by route
        cursor.execute("""
            SELECT origin_airport, dest_airport, COUNT(*) as count
            FROM historical_flights
            GROUP BY origin_airport, dest_airport
            ORDER BY count DESC
        """)
        routes = cursor.fetchall()

        conn.close()

        return {
            "database_stats": {
                "total_flights": total_flights,
                "complete_weather_data": complete_weather,
                "missing_weather_data": missing_weather,
                "completion_percentage": round((complete_weather / total_flights * 100) if total_flights > 0 else 0, 2),
                "cancelled_flights": cancelled,
                "completed_flights": completed,
                "cancellation_rate": round((cancelled / total_flights * 100) if total_flights > 0 else 0, 2),
                "date_range": {
                    "earliest": date_range[0] if date_range[0] else None,
                    "latest": date_range[1] if date_range[1] else None
                }
            },
            "weather_conditions": {
                "puw": {
                    "low_visibility": low_vis_puw,
                    "high_winds": high_wind_puw,
                    "freezing_temps": freezing_puw
                },
                "origin_airports": {
                    "low_visibility": low_vis_origin,
                    "high_winds": high_wind_origin
                },
                "destination_airports": {
                    "low_visibility": low_vis_dest
                }
            },
            "routes": [
                {
                    "origin": r[0],
                    "destination": r[1],
                    "flights": r[2]
                }
                for r in routes
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/database")
async def get_full_database(limit: int = 1000, offset: int = 0):
    """
    Admin endpoint - Returns paginated full database with all weather data.
    Shows multi-airport weather if backfilled.
    """
    try:
        conn = fd.history_db._get_conn()
        cursor = conn.cursor()

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM historical_flights")
        total = cursor.fetchone()[0]

        # Get paginated data with ALL columns
        cursor.execute("""
            SELECT
                flight_number, flight_date, is_cancelled,
                origin_airport, dest_airport,
                puw_visibility_miles, puw_wind_speed_knots, puw_wind_direction,
                puw_temp_f, puw_weather_code,
                origin_visibility_miles, origin_wind_speed_knots, origin_wind_direction,
                origin_temp_f, origin_weather_code,
                dest_visibility_miles, dest_wind_speed_knots, dest_wind_direction,
                dest_temp_f, dest_weather_code
            FROM historical_flights
            ORDER BY flight_date DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = cursor.fetchall()
        conn.close()

        flights = []
        for row in rows:
            flight = {
                "flight_number": row[0],
                "flight_date": row[1],
                "is_cancelled": bool(row[2]),
                "origin_airport": row[3],
                "dest_airport": row[4],
                "multi_airport_weather": {
                    "KPUW": {
                        "visibility_miles": row[5],
                        "wind_speed_knots": row[6],
                        "wind_direction": row[7],
                        "temperature_f": row[8],
                        "weather_code": row[9]
                    } if row[5] is not None else None,
                    row[3]: {
                        "visibility_miles": row[10],
                        "wind_speed_knots": row[11],
                        "wind_direction": row[12],
                        "temperature_f": row[13],
                        "weather_code": row[14]
                    } if row[10] is not None and row[3] else None,
                    row[4]: {
                        "visibility_miles": row[15],
                        "wind_speed_knots": row[16],
                        "wind_direction": row[17],
                        "temperature_f": row[18],
                        "weather_code": row[19]
                    } if row[15] is not None and row[4] else None
                }
            }
            flights.append(flight)

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "flights": flights
        }
    except Exception as e:
        logger.error(f"Error fetching full database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Mount Static Files (Frontend)
# Must be after API routes to avoid conflict
frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # API routes are already handled above.
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    # Try to serve static files first (favicon, sitemap, robots.txt, manifest, etc.)
    static_file_path = os.path.join(frontend_dist, full_path)
    if os.path.isfile(static_file_path):
        return FileResponse(static_file_path)

    # Otherwise serve index.html for SPA routing
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built. Run 'npm run build' in frontend/"}
