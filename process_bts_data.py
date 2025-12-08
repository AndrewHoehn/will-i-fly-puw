import zipfile
import os
import pandas as pd
import glob

def process_zips():
    source_dir = "BoT Statistics"
    dest_dir = "BoT Statistics/processed"
    os.makedirs(dest_dir, exist_ok=True)
    
    zip_files = glob.glob(os.path.join(source_dir, "*.zip"))
    
    found_months = []
    
    print(f"Found {len(zip_files)} zip files.")
    
    for zip_path in zip_files:
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # The main data file is usually T_ONTIME_REPORTING.csv
                # We'll read it directly into pandas to check the date
                with z.open('T_ONTIME_REPORTING.csv') as f:
                    # Read just the first few rows to get the date
                    df = pd.read_csv(f, nrows=5)
                    
                    # Columns are usually YEAR, MONTH, etc.
                    if 'YEAR' in df.columns and 'MONTH' in df.columns:
                        year = df['YEAR'].iloc[0]
                        month = df['MONTH'].iloc[0]
                        
                        new_name = f"FlightData_{year}_{month:02d}.csv"
                        dest_path = os.path.join(dest_dir, new_name)
                        
                        # Extract and write the full file to the new name
                        # We have to re-open to read the whole thing or just extract and rename
                        # Extracting and renaming is safer for memory
                        z.extract('T_ONTIME_REPORTING.csv', path=dest_dir)
                        
                        # Rename
                        extracted_path = os.path.join(dest_dir, 'T_ONTIME_REPORTING.csv')
                        if os.path.exists(dest_path):
                            print(f"Warning: {new_name} already exists. Overwriting.")
                        os.rename(extracted_path, dest_path)
                        
                        found_months.append((year, month))
                        print(f"Processed {os.path.basename(zip_path)} -> {new_name}")
                    else:
                        print(f"Error: Could not find YEAR/MONTH in {zip_path}")
                        
        except Exception as e:
            print(f"Failed to process {zip_path}: {e}")

    # Identify missing months
    print("\n--- Summary ---")
    found_months.sort()
    
    # Generate expected list (Jan 2023 - Dec 2024)
    expected = []
    for y in [2023, 2024]:
        for m in range(1, 13):
            expected.append((y, m))
            
    missing = [m for m in expected if m not in found_months]
    
    if missing:
        print("Missing Months:")
        for y, m in missing:
            print(f"{y}-{m:02d}")
    else:
        print("All months accounted for!")

if __name__ == "__main__":
    process_zips()
