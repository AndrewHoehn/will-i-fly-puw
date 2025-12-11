"""
Verify historical flight routes against AeroDataBox API.
"""

import os
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

flights_to_verify = [
    ("AS 2152", "2025-08-20", "KSEA", "KPUW"),
    ("AS 2132", "2025-08-02", "KPUW", "KSEA"),
    ("AS 2036", "2025-11-11", "KBOI", "KPUW"),
    ("AS 2438", "2025-07-18", "KSEA", "KPUW"),
    ("AS 2132", "2025-07-22", "KPUW", "KSEA"),
    ("AS 2364", "2025-09-28", "KSEA", "KPUW"),
    ("AS 2152", "2025-08-29", "KSEA", "KPUW"),
    ("AS 2036", "2025-10-27", "KBOI", "KPUW"),
    ("AS 2067", "2025-07-07", "KPUW", "KSEA"),
    ("AS 2152", "2025-11-20", "KSEA", "KPUW"),
]

def verify_flight(flight_number, date_str, expected_origin, expected_dest):
    """
    Verify a flight's route against AeroDataBox API.

    Args:
        flight_number: Flight number (e.g., "AS 2152")
        date_str: Date string "YYYY-MM-DD"
        expected_origin: Expected origin airport (e.g., "KSEA")
        expected_dest: Expected destination airport (e.g., "KPUW")

    Returns:
        tuple: (is_correct, actual_origin, actual_dest)
    """
    # Parse flight number (remove spaces, split airline/number)
    parts = flight_number.strip().split()
    if len(parts) != 2:
        logger.error(f"Invalid flight number format: {flight_number}")
        return (False, None, None)

    airline_code = parts[0]
    flight_num = parts[1]

    # AeroDataBox API endpoint for specific flight on a date
    url = f"https://aerodatabox.p.rapidapi.com/flights/number/{airline_code}{flight_num}/{date_str}"

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            logger.warning(f"No data found for {flight_number} on {date_str}")
            return (None, None, None)

        # Find the flight for PUW (could be multiple flights with same number on same day)
        for flight in data:
            dep_airport = flight.get('departure', {}).get('airport', {}).get('icao')
            arr_airport = flight.get('arrival', {}).get('airport', {}).get('icao')

            # Check if this flight involves PUW
            if dep_airport == 'KPUW' or arr_airport == 'KPUW':
                is_correct = (dep_airport == expected_origin and arr_airport == expected_dest)
                return (is_correct, dep_airport, arr_airport)

        logger.warning(f"No PUW flight found in data for {flight_number} on {date_str}")
        return (None, None, None)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Flight not found: {flight_number} on {date_str}")
        else:
            logger.error(f"API error for {flight_number}: {e}")
        return (None, None, None)
    except Exception as e:
        logger.error(f"Error verifying {flight_number}: {e}")
        return (None, None, None)

def main():
    if not RAPIDAPI_KEY:
        logger.error("RAPIDAPI_KEY environment variable not set!")
        return

    logger.info(f"Verifying {len(flights_to_verify)} flights against AeroDataBox API...")
    logger.info("")

    correct = 0
    incorrect = 0
    not_found = 0

    for flight_number, date_str, expected_origin, expected_dest in flights_to_verify:
        logger.info(f"Checking {flight_number} on {date_str}...")
        logger.info(f"  Expected: {expected_origin} → {expected_dest}")

        is_correct, actual_origin, actual_dest = verify_flight(
            flight_number, date_str, expected_origin, expected_dest
        )

        if is_correct is None:
            not_found += 1
            logger.info(f"  Result: ⚠️  NOT FOUND in API")
        elif is_correct:
            correct += 1
            logger.info(f"  Result: ✅ CORRECT")
        else:
            incorrect += 1
            logger.info(f"  Result: ❌ INCORRECT - Actual: {actual_origin} → {actual_dest}")

        logger.info("")

    logger.info("=" * 60)
    logger.info(f"Summary: {correct} correct, {incorrect} incorrect, {not_found} not found")
    logger.info(f"Accuracy: {correct}/{correct+incorrect} ({100*correct/(correct+incorrect) if (correct+incorrect) > 0 else 0:.1f}%)")

if __name__ == "__main__":
    main()
