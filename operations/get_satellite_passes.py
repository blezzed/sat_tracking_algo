
"""
get_satellite_passes.py

Module to fetch Two-Line Element (TLE) data, compute satellite pass events (rise, culmination, set)
for a given ground station over the next 2 days, using Skyfield.
Returns a dict mapping satellite names to lists of pass event dicts.
"""
from skyfield.api import wgs84, load, EarthSatellite  # Satellite and geodetic utilities
from datetime import datetime, timedelta
import pytz

from repo.api import fetch_and_parse_satellite_data  # Fetches TLEs from API/database
from values import API_URL_SATELLITES            # URL endpoint for satellite TLE data


def get_satellite_passes(gs):
    """
    Calculate upcoming satellite pass events for a ground station.

    Args:
        gs (object): Ground station object with attributes:
                     - latitude (float): degrees North
                     - longitude (float): degrees East
                     - start_tracking_elevation (float): minimum elevation angle (deg)

    Returns:
        dict: Keys are satellite names, values are lists of dicts for each event:
              {
                  'event_time': 'YYYY-MM-DD HH:MM:SS',  # Local time string
                  'event': 'Satellite Rise'|'culminate'|'Satellite Set',
                  'elevation': float,  # degrees
                  'azimuth': float,    # degrees
                  'distance': float    # kilometers
              }
    """
    # 1. Get current local time at Africa/Maputo
    now = datetime.now(pytz.timezone('Africa/Maputo'))

    # 2. Initialize Skyfield timescale and compute time window
    ts = load.timescale()
    start_time = ts.from_datetime(now)
    end_time = ts.from_datetime(now + timedelta(days=2))  # Next 2 days

    # 3. Define ground station position for Skyfield
    ground_station = wgs84.latlon(gs.latitude, gs.longitude)

    # 4. Fetch TLE data list from API/database
    tle_data = fetch_and_parse_satellite_data(API_URL_SATELLITES)

    all_satellite_passes = {}

    # 5. Loop through each TLE record
    for tle in tle_data:
        # Create Skyfield EarthSatellite object
        satellite = EarthSatellite(tle.line1, tle.line2, tle.name, ts)
        # Find rise, culmination, and set events over time window
        times, events = satellite.find_events(
            ground_station,
            start_time,
            end_time,
            altitude_degrees=gs.start_tracking_elevation
        )

        print(f"Processing satellite: {satellite.name}")  # Debug log

        passes_list = []  # Collect pass event details
        event_names = ('Satellite Rise', 'culminate', 'Satellite Set')

        # 6. Iterate over each event time and type
        for ti, event in zip(times, events):
            # Map event index to human-readable name
            name = event_names[event]

            # Convert Skyfield time to UTC datetime, then adjust to local
            event_time = ti.utc_datetime()
            # Replace tzinfo and add offset for Maputo local (UTC+2)
            event_time = event_time.replace(tzinfo=pytz.utc) + timedelta(hours=2)

            # Calculate topocentric position to get alt/az and slant distance
            topo = (satellite - ground_station).at(ti)
            alt, az, distance = topo.altaz()

            # Append a dict describing this event
            passes_list.append({
                'event_time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
                'event': name,
                'elevation': round(alt.degrees, 1),
                'azimuth': round(az.degrees, 1),
                'distance': round(distance.km, 1)
            })

        # 7. Store the list for this satellite by its name
        all_satellite_passes[satellite.name] = passes_list

    # 8. Return dict of all computed passes
    return all_satellite_passes
