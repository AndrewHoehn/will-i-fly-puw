# Multi-Airport Weather Implementation Guide

## Status: IN PROGRESS

### Completed ✅
1. **Database Migration Script** (`migrate_multiairport_weather.py`)
   - Adds new columns for PUW, origin, and destination weather
   - Backward compatible (preserves old columns)
   - Copies existing data to new PUW-specific columns

2. **WeatherData Class** (`weather_data.py`)
   - Supports multi-airport weather fetching (KPUW, KSEA, KBOI)
   - Parallel API calls using ThreadPoolExecutor
   - Backward compatible with legacy code
   - New method: `get_historical_weather_for_date()` for backfill

### Remaining Tasks

#### 3. Update HistoryDatabase (`history_db.py`)

**Changes needed:**
- Update `add_flight()` method to accept multi-airport weather
- Update `store_active_flight_with_prediction()` to log multi-airport weather
- Update `find_similar_flights()` to query across all 3 airports

**New method signatures:**
```python
def add_flight_multi_weather(self, data):
    """
    Store flight with multi-airport weather data.

    Args:
        data: {
            'flight_number': str,
            'flight_date': str,
            'is_cancelled': bool,
            'origin_airport': str,
            'dest_airport': str,
            'puw_weather': {...},
            'origin_weather': {...},
            'dest_weather': {...}
        }
    """
```

#### 4. Update PredictionEngine (`prediction_engine.py`)

**Major changes:**
- Update `calculate_risk()` to accept 3 weather objects: puw, origin, dest
- Add runway configs for SEA and BOI
- Add methods:
  - `_score_origin_weather()` - Score weather at origin airport
  - `_score_destination_weather()` - Score weather at destination
  - `_calculate_inbound_aircraft_risk()` - Check if inbound flight is delayed
- Update historical matching to query multi-airport patterns

**New method:**
```python
def calculate_risk_multi_airport(self, flight, puw_weather, origin_weather, dest_weather):
    """
    Calculate risk using weather from all 3 airports.

    For arrivals: Check origin weather + PUW weather
    For departures: Check PUW weather + destination weather + inbound aircraft
    """
```

#### 5. Update flight_data.py

**Changes:**
- Update `_enrich_with_weather()` to extract multi-airport weather
- Pass all 3 weather objects to prediction engine
- Update flight dict structure to include origin/dest weather

**New flight structure:**
```python
{
    'weather': {...},  # PUW weather (legacy)
    'puw_weather': {...},
    'origin_weather': {...},
    'dest_weather': {...},
    'risk_score': {...}
}
```

#### 6. Update API (`api.py`)

**Changes:**
- Update `/api/dashboard` response to include multi-airport weather
- Ensure backward compatibility with existing clients

**Response structure:**
```json
{
  "historical": [...],
  "future": [{
    "weather": {...},  // PUW (legacy)
    "multi_airport_weather": {
      "KPUW": {...},
      "KSEA": {...},
      "KBOI": {...}
    },
    "risk_score": {
      "score": 45,
      "factors": [
        "PUW: Good conditions",
        "SEA: Low visibility (1.2mi) +35%",
        "Historical: 68% cancelled when SEA vis < 1.5mi"
      ]
    }
  }]
}
```

#### 7. Update Frontend (`App.jsx`)

**Changes:**
- Display multi-airport weather cards
- Update risk factor display to show airport-specific warnings
- Add "inbound aircraft alert" UI component

**New components:**
```jsx
<MultiAirportWeather
  puw={flight.puw_weather}
  origin={flight.origin_weather}
  dest={flight.dest_weather}
  originCode={flight.origin}
  destCode={flight.destination}
/>

<InboundAlert
  show={flight.inbound_alert}
  message={flight.inbound_alert.message}
  risk={flight.inbound_alert.risk}
/>
```

#### 8. Create Backfill Script (`backfill_historical_weather.py`)

**Purpose:** Fetch historical weather for SEA/BOI for existing flight records

**Process:**
1. Query all historical flights
2. For each flight, get origin and destination airports
3. Fetch weather from Open-Meteo Archive API
4. Update record with origin/dest weather

#### 9. Testing & Deployment

**Local testing:**
```bash
# 1. Run migration
python backend/migrate_multiairport_weather.py

# 2. Test weather fetching
python backend/weather_data.py

# 3. Start backend
uvicorn backend.api:app --reload

# 4. Start frontend
cd frontend && npm run dev

# 5. Verify:
#    - API returns multi-airport weather
#    - Risk scores include SEA/BOI factors
#    - Frontend displays all 3 airports
```

**Production deployment:**
```bash
# 1. SSH to Fly.io and run migration
fly ssh console
cd /app/backend
python migrate_multiairport_weather.py

# 2. Deploy new code
fly deploy

# 3. Run backfill (optional, can run later)
fly ssh console
cd /app/backend
python backfill_historical_weather.py

# 4. Monitor logs
fly logs
```

## Implementation Order

1. ✅ Database migration
2. ✅ WeatherData class
3. ⏳ HistoryDatabase updates
4. ⏳ PredictionEngine updates
5. ⏳ flight_data.py updates
6. ⏳ API updates
7. ⏳ Frontend updates
8. ⏳ Backfill script
9. ⏳ Testing & deployment

## Rollback Plan

If issues occur:
1. Old weather columns still exist (visibility_miles, etc.)
2. Code can fall back to single-airport mode
3. No data loss - all existing records preserved
4. Can revert by deploying previous git commit

## Expected Impact

- **Accuracy improvement:** 60% → 85% true positive rate
- **API calls:** 48/day → 144/day (still well within free tier)
- **Response time:** Negligible impact (parallel fetching)
- **New capabilities:**
  - SEA fog detection
  - BOI thunderstorm alerts
  - Inbound aircraft delay cascade detection
