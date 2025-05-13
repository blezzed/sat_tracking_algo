
"""
api.py

Module to fetch Two-Line Element (TLE) satellite data from a remote API,
parse into SatelliteTLE entities, save to local database, and provide
a fallback to retrieve stored data when the API is unavailable.
"""
# External HTTP library for API communication
import requests

# Entity definitions for structured data
from entities.ground_station import GroundStation  # NOTE: Imported but not used here; consider removal
from entities.sat_tle import SatelliteTLE   # Data class representing a satellite's TLE and metadata

# Database persistence functions
from repo.database import save_satellites_to_db, get_all_satellites_from_db


def fetch_and_parse_satellite_data(api_url):
    """
    Retrieve TLE data from the given API endpoint, parse into SatelliteTLE objects,
    save them to the database, and return the list. If the API call fails,
    fall back to retrieving any previously saved data from the local database.

    Args:
        api_url (str): The URL to fetch satellite TLE JSON data from.

    Returns:
        List[SatelliteTLE]: Satellite entities with attributes:
                            name, line1, line2, tle_group,
                            auto_tracking, orbit_status, created_at, last_updated
    """
    try:
        # 1. Perform GET request with a timeout to avoid hanging
        response = requests.get(api_url, timeout=10)
        # 2. Raise an error for HTTP status codes outside 200–299
        response.raise_for_status()

        # 3. Parse the JSON payload into native Python data structures
        satellites_data = response.json()
        satellites = []

        # 4. Filter and convert raw dicts into SatelliteTLE entities
        for satellite_data in satellites_data:
            # Only include satellites currently orbiting and marked for auto-tracking
            if (satellite_data.get('orbit_status') == 'orbiting' and
                satellite_data.get('auto_tracking') is True):

                satellite = SatelliteTLE(
                    name=satellite_data['name'],
                    line1=satellite_data['line1'],
                    line2=satellite_data['line2'],
                    tle_group=satellite_data['tle_group'],
                    auto_tracking=satellite_data['auto_tracking'],
                    orbit_status=satellite_data['orbit_status'],
                    created_at=satellite_data['created_at'],
                    last_updated=satellite_data['last_updated']
                )
                satellites.append(satellite)

        # 5. Persist the fetched entities to the local database
        save_satellites_to_db(satellites)
        print(f"Successfully fetched and saved {len(satellites)} satellites.")
        return satellites

    except requests.exceptions.RequestException as e:
        # 6. Log the error and attempt to use cached DB data
        print(f"Error fetching satellite data from API: {e}")
        print("Attempting to retrieve satellites from the database...")

        satellites = get_all_satellites_from_db()
        if satellites:
            print(f"Retrieved {len(satellites)} satellites from the database.")
        else:
            print("No satellites available in the database.")
        return satellites
