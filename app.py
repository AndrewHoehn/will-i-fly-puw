import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from flight_data import FlightData
from weather_data import WeatherData
from faa_data import FAAStatusAPI

# Page Config
st.set_page_config(
    page_title="KPUW Flight Reliability",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS for "Departure Board" Look
st.markdown("""
<style>
    .flight-row {
        background-color: #262730;
        padding: 8px 15px;
        border-radius: 5px;
        margin-bottom: 6px;
        border-left: 4px solid #4b4b4b;
    }
    .flight-row:hover {
        background-color: #363740;
    }
    .time-big {
        font-size: 1.0em;
        font-weight: bold;
        color: #ffffff;
        line-height: 1.2;
    }
    .time-small {
        font-size: 0.75em;
        color: #a0a0a0;
        line-height: 1.2;
    }
    .flight-num {
        font-size: 1.0em;
        font-weight: bold;
        color: #4da6ff;
        line-height: 1.2;
    }
    .route {
        font-size: 0.9em;
        color: #e0e0e0;
        line-height: 1.2;
    }
    .status-badge {
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85em;
        font-weight: bold;
        text-align: center;
        color: white;
        display: inline-block;
        width: 100%;
    }
    .status-green { background-color: #28a745; }
    .status-red { background-color: #dc3545; }
    .status-orange { background-color: #fd7e14; }
    .status-gray { background-color: #6c757d; }
    
    /* Hide Streamlit's default padding for a tighter look */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("✈️ KPUW Flight Board")
st.markdown("Real-time reliability for **Pullman/Moscow (KPUW)** ⇄ **Seattle (KSEA) / Boise (KBOI)**")

# Initialize Data Loaders
def load_data_from_db():
    fd = FlightData()
    wd = WeatherData()
    
    # Get flights from DB
    flights = fd.get_flights(days_back=7, hours_forward=48)
    
    # Fetch weather for these flights
    weather_map = wd.get_weather_for_flights(flights)
    
    # Fetch TAF
    taf = wd.get_taf()
    
    return flights, weather_map, taf, wd, fd

def get_faa_status():
    faa = FAAStatusAPI()
    sea_status = faa.get_airport_status("SEA")
    boi_status = faa.get_airport_status("BOI")
    return sea_status, boi_status

# Sidebar / Header Controls
with st.sidebar:
    st.header("Controls")
    
    # Show last updated
    fd_temp = FlightData()
    last_up = fd_temp.get_last_updated_str()
    st.caption(f"Last Updated: {last_up}")
    
    if st.button("🔄 Refresh Data"):
        with st.spinner("Syncing with live data..."):
            msg = fd_temp.smart_sync()
            st.success(msg)
            st.cache_data.clear() # Clear cache to reload DB
            st.rerun()
            
    st.divider()
    st.header("FAA Hub Status")
    
    sea, boi = get_faa_status()
    
    def status_indicator(code, status_obj):
        color = "green"
        icon = "✅"
        if status_obj['status'] == "Ground Stop":
            color = "red"
            icon = "🛑"
        elif status_obj['status'] in ["Ground Delay", "Warning", "Delay"]:
            color = "orange"
            icon = "⚠️"
            
        st.markdown(f"**{code}** {icon} :{color}[{status_obj['status']}]")
        if status_obj.get('details'):
            st.caption(status_obj['details'])

    status_indicator("SEA", sea)
    status_indicator("BOI", boi)

flights, weather_map, taf, wd_instance, fd_instance = load_data_from_db()

# Helper: Render Flight Row
def render_flight_row(f, is_future=False, aircraft_map=None):
    # --- Prepare Data ---
    # Time
    from dateutil import tz
    to_zone = tz.gettz('America/Los_Angeles')
    from_zone = tz.tzutc()

    sched_str = f['local_time'].strftime("%H:%M")
    actual_str = ""
    if f.get('actual_time'):
        act_local = f['actual_time'].astimezone(to_zone)
        actual_str = act_local.strftime("%H:%M")
    
    # Status Logic
    status_raw = f['status'].upper()
    
    # Fix "Unknown" for future flights
    if is_future and status_raw == 'UNKNOWN':
        status_raw = 'SCHEDULED'
        
    status_color = "status-gray"
    status_icon = ""
    
    if status_raw in ['LANDED', 'ARRIVED']:
        status_color = "status-green"
        status_icon = ""
    elif status_raw in ['CANCELLED', 'CANCELED']:
        status_color = "status-red"
        status_icon = "✕ "
    elif status_raw in ['ACTIVE', 'DEPARTED', 'EN ROUTE']:
        status_color = "status-green"
        status_icon = "✈ "
    elif status_raw in ['SCHEDULED', 'EXPECTED']:
        status_color = "status-green"
        status_icon = ""
    else:
        status_color = "status-orange" # Delayed, Unknown, etc.
        
    # Route
    if f['type'] == 'arrival':
        route_icon = "🛬"
        route_text = f"From {f['origin']}"
    else:
        route_icon = "🛫"
        route_text = f"To {f['destination']}"
        
    # Inbound Risk (Future only)
    inbound_alert = None
    if is_future and f['type'] == 'departure' and aircraft_map:
        reg = f.get('aircraft_reg')
        if reg and reg != 'Unknown':
            plane_flights = aircraft_map.get(reg, [])
            try:
                idx = next(i for i, x in enumerate(plane_flights) if x['id'] == f['id'])
                if idx > 0:
                    inbound = plane_flights[idx-1]
                    in_stat = inbound['status'].lower()
                    if in_stat in ['cancelled', 'canceled']:
                        inbound_alert = f"⚠️ INBOUND CANCELLED ({inbound['number']})"
                        status_color = "status-red" # Upgrade status to red
                    elif in_stat in ['active', 'landed']:
                         pass # Good
                    elif in_stat not in ['scheduled']:
                         inbound_alert = f"ℹ️ Inbound: {inbound['status']}"
            except StopIteration:
                pass

    # Weather (Forecast or Historical)
    weather_alert = None
    sched_utc = f['scheduled_time']
    lookup_time = sched_utc.replace(minute=0, second=0, microsecond=0)
    if sched_utc.minute >= 30:
        lookup_time = lookup_time + timedelta(hours=1)
    lookup_time_naive = lookup_time.replace(tzinfo=None)
    
    w_cond = weather_map.get(lookup_time_naive) or weather_map.get(lookup_time)
    if w_cond:
        flags = wd_instance.check_conditions(w_cond)
        if flags:
            weather_alert = f"☁️ Weather Risk: {', '.join(flags)}"
            if status_color == "status-green": status_color = "status-orange"

    # --- Render Row ---
    with st.container():
        # Custom HTML structure for the row
        # We use columns for layout
        c1, c2, c3, c4 = st.columns([1.2, 2.5, 1.5, 1.8])
        
        with c1:
            st.markdown(f"<div class='time-big'>{sched_str}</div>", unsafe_allow_html=True)
            if actual_str:
                st.markdown(f"<div class='time-small'>Act: {actual_str}</div>", unsafe_allow_html=True)
            elif is_future:
                 st.markdown(f"<div class='time-small'>Sched</div>", unsafe_allow_html=True)
                 
        with c2:
            st.markdown(f"<div class='flight-num'>{f['airline']} {f['number']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='route'>{route_icon} {route_text}</div>", unsafe_allow_html=True)
            
        with c3:
            st.caption(f"Reg: {f.get('aircraft_reg', '--')}")
            # Removed model to save space or keep it if short
                
        with c4:
            st.markdown(f"<div class='status-badge {status_color}'>{status_icon}{status_raw}</div>", unsafe_allow_html=True)
            
        # Alerts Row (Full Width)
        if inbound_alert or weather_alert:
            alert_col = st.columns(1)[0]
            if inbound_alert:
                alert_col.error(inbound_alert)
            if weather_alert:
                alert_col.warning(weather_alert)
                
        # No divider, rely on margin

# Process Data for Display
if not flights:
    st.info("Local database is empty. Click 'Refresh Data' to fetch initial data.")
else:
    # Timezone Setup
    from dateutil import tz
    to_zone = tz.gettz('America/Los_Angeles')
    from_zone = tz.tzutc()
    
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(to_zone)

    # Convert all flights to Local Time
    for f in flights:
        if f.get('scheduled_time'):
            if f['scheduled_time'].tzinfo is None:
                 f['scheduled_time'] = f['scheduled_time'].replace(tzinfo=from_zone)
            f['local_time'] = f['scheduled_time'].astimezone(to_zone)
        else:
            f['local_time'] = None

    # Inbound Linking Map
    aircraft_map = {}
    for f in flights:
        reg = f.get('aircraft_reg')
        if reg and reg != 'Unknown':
            if reg not in aircraft_map:
                aircraft_map[reg] = []
            aircraft_map[reg].append(f)
    for reg in aircraft_map:
        aircraft_map[reg].sort(key=lambda x: x['scheduled_time'])

    # Split Data
    historical_flights = [f for f in flights if f['local_time'] and f['local_time'] <= now_local]
    tomorrow_end = (now_local + timedelta(days=1)).replace(hour=23, minute=59, second=59) + timedelta(hours=1)
    future_flights = [f for f in flights if f['local_time'] and f['local_time'] > now_local and f['local_time'] <= tomorrow_end]
    
    historical_flights.sort(key=lambda x: x['local_time'], reverse=True)
    future_flights.sort(key=lambda x: x['local_time'])

    # Tabs
    tab1, tab2 = st.tabs(["📜 Past Flights", "🔮 Upcoming Board"])

    with tab1:
        # Stats
        total = len(historical_flights)
        cx = len([f for f in historical_flights if f['status'].lower() in ['cancelled', 'canceled']])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Flights (7d)", total)
        c2.metric("Cancelled", f"{cx} ({cx/total*100:.1f}%)" if total else "0")
        
        st.divider()
        
        current_day = None
        for f in historical_flights:
            f_day = f['local_time'].strftime("%A, %b %d")
            if f_day != current_day:
                st.subheader(f_day)
                current_day = f_day
            render_flight_row(f, is_future=False)

    with tab2:
        if taf:
            with st.expander("METAR/TAF Report", expanded=False):
                st.code(taf)
        st.divider()
        
        current_day = None
        for f in future_flights:
            f_day = f['local_time'].strftime("%A, %b %d")
            if f_day != current_day:
                st.subheader(f_day)
                current_day = f_day
            render_flight_row(f, is_future=True, aircraft_map=aircraft_map)

# Footer
st.markdown("---")
st.caption("Data Sources: FlightRadar24 (Unofficial), Open-Meteo, AVWX.")
