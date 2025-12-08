import pandas as pd
import sys
import os

# Add current dir to path to import history_db
sys.path.append(os.path.dirname(__file__))
from .history_db import HistoryDatabase

def ingest_csv():
    csv_path = os.path.join(os.path.dirname(__file__), "../historical_flight_data/kpuw_master_training_data.csv")
    if not os.path.exists(csv_path):
        print(f"Error: CSV not found at {csv_path}")
        return

    print("Loading CSV...")
    df = pd.read_csv(csv_path)
    
    db = HistoryDatabase()
    
    print(f"Ingesting {len(df)} rows...")
    count = 0
    
    for _, row in df.iterrows():
        # Conversions
        # Temp: C -> F
        temp_c = row.get('actual_temp_c')
        temp_f = (temp_c * 9/5) + 32 if pd.notnull(temp_c) else None
        
        # Wind: km/h -> knots (1 km/h = 0.539957 kts)
        wind_kmh = row.get('actual_wind_speed_kmh')
        wind_kts = wind_kmh * 0.539957 if pd.notnull(wind_kmh) else None
        
        # Visibility: meters -> miles (1 m = 0.000621371 miles)
        vis_m = row.get('actual_visibility_m')
        if pd.isnull(vis_m):
            vis_m = row.get('forecast_visibility_m')
            
        vis_mi = vis_m * 0.000621371 if pd.notnull(vis_m) else None
        
        # Snowfall
        snow_cm = row.get('actual_snowfall_cm')
        if pd.isnull(snow_cm): snow_cm = 0.0
        
        data = {
            'flight_number': row.get('flight_number'),
            'flight_date': row.get('flight_date'),
            'is_cancelled': row.get('is_cancelled'),
            'visibility_miles': vis_mi,
            'wind_speed_knots': wind_kts,
            'temp_f': temp_f,
            'snowfall_cm': snow_cm,
            'weather_code': row.get('actual_weather_code')
        }
        
        db.add_flight(data)
        count += 1
        
    print(f"Successfully ingested {count} flights into history.db")

if __name__ == "__main__":
    ingest_csv()
