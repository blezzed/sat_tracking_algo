import requests

from entities.ground_station import GroundStation
from entities.sat_tle import SatelliteTLE
from repo.database import save_satellites_to_db, get_all_satellites_from_db


def fetch_and_parse_satellite_data(api_url):
    try:
        # Attempt to fetch data from the API
        response = requests.get(api_url, timeout=10)  # Timeout to avoid long delays
        response.raise_for_status()  # Raise an HTTPError for bad responses

        satellites_data = response.json()  # Parse JSON response
        satellites = []

        for satellite_data in satellites_data:
            if satellite_data['orbit_status'] == 'orbiting' and satellite_data['auto_tracking'] == True:
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

        # Save the fetched data to the database
        save_satellites_to_db(satellites)
        print(f"Successfully fetched and saved {len(satellites)} satellites.")
        return satellites

    except requests.exceptions.RequestException as e:
        print(f"Error fetching satellite data from API: {e}")
        print("Attempting to retrieve satellites from the database...")

        # Retrieve data from the database as a fallback
        satellites = get_all_satellites_from_db()
        if satellites:
            print(f"Retrieved {len(satellites)} satellites from the database.")
        else:
            print("No satellites available in the database.")
        return satellites



