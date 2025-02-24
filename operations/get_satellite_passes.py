from skyfield.api import wgs84, load, EarthSatellite
from datetime import datetime, timedelta
import pytz

from repo.api import fetch_and_parse_satellite_data
from values import API_URL_SATELLITES


def get_satellite_passes(gs):
    # Get the current time (Africa/Maputo timezone)
    now = datetime.now(pytz.timezone('Africa/Maputo'))

    # Load Skyfield timescale
    ts = load.timescale()

    start_time = ts.from_datetime(now)
    end_time = ts.from_datetime(now + timedelta(days=2))  # Look for passes for the next 3 days

    #gs = fetch_ground_stations(API_URL_GROUND_STATIONS)[0]

    ground_station = wgs84.latlon(gs.latitude, gs.longitude)

    # Fetch TLE data from the database
    tle_data = fetch_and_parse_satellite_data(API_URL_SATELLITES)

    all_satellite_passes = {}

    for tle in tle_data:
        satellite = EarthSatellite(tle.line1, tle.line2, tle.name, ts)
        t, events = satellite.find_events(ground_station, start_time, end_time,
                                          altitude_degrees=gs.start_tracking_elevation)

        print(f"Processing satellite: {satellite.name}")

        passes_list = []

        event_names = 'Satellite Rise', 'culminate', 'Satellite Set'
        for ti, event in zip(t, events):
            name = event_names[event]

            event_time = ti.utc_datetime()
            event_time = event_time.replace(tzinfo=pytz.utc) + timedelta(hours=2)  # Adjusting to local timezone

            # Calculate elevation, azimuth, and distance
            topo_centric = (satellite - ground_station).at(ti)
            alt, az, distance = topo_centric.altaz()

            # Add pass info to the list for return
            passes_list.append({
                'event_time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
                'event': name,
                'elevation': round(alt.degrees, 1),
                'azimuth': round(az.degrees, 1),
                'distance': round(distance.km, 1)
            })

        all_satellite_passes[satellite.name] = passes_list

    return all_satellite_passes
