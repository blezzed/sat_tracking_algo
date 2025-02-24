import mariadb
import requests

from entities.ground_station import GroundStation
from entities.sat_tle import SatelliteTLE
from values import DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE


def save_satellites_to_db(satellites):
    try:
        # Connect to the database
        connection = mariadb.connect(
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            database=DATABASE
        )
        cursor = connection.cursor()

        for satellite in satellites:
            # Check if the satellite already exists by its name
            cursor.execute(
                "SELECT COUNT(*) FROM SatelliteTLE WHERE name = ?",
                (satellite.name,)
            )
            exists = cursor.fetchone()[0] > 0

            if exists:
                # Update the existing satellite
                cursor.execute(
                    """
                    UPDATE SatelliteTLE
                    SET line1 = ?, line2 = ?, tle_group = ?, auto_tracking = ?, 
                        orbit_status = ?, last_updated = ?
                    WHERE name = ?
                    """,
                    (
                        satellite.line1, satellite.line2, satellite.tle_group,
                        satellite.auto_tracking, satellite.orbit_status,
                        satellite.last_updated, satellite.name
                    )
                )
                print(f"Updated satellite: {satellite.name}")
            else:
                # Insert a new satellite
                cursor.execute(
                    """
                    INSERT INTO SatelliteTLE 
                    (name, line1, line2, tle_group, auto_tracking, orbit_status, created_at, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        satellite.name, satellite.line1, satellite.line2, satellite.tle_group,
                        satellite.auto_tracking, satellite.orbit_status,
                        satellite.created_at, satellite.last_updated
                    )
                )
                print(f"Inserted new satellite: {satellite.name}")

        # Commit the changes
        connection.commit()

    except mariadb.Error as e:
        print(f"Error saving satellites to database: {e}")
    finally:
        if connection:
            connection.close()


def get_all_satellites_from_db():
    satellites = []
    try:
        connection = mariadb.connect(
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            database=DATABASE
        )
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name, line1, line2, tle_group, auto_tracking, orbit_status, created_at, last_updated FROM SatelliteTLE WHERE orbit_status = 'orbiting' AND auto_tracking = TRUE")

        for row in cursor.fetchall():
            satellite = SatelliteTLE(
                name=row[0],
                line1=row[1],
                line2=row[2],
                tle_group=row[3],
                auto_tracking=row[4],
                orbit_status=row[5],
                created_at=row[6],
                last_updated=row[7]
            )
            satellites.append(satellite)
    except mariadb.Error as e:
        print(f"Error retrieving satellites from database: {e}")
    finally:
        if connection:
            connection.close()

    return satellites


def save_ground_stations_to_db(ground_stations):
    try:
        # Connect to the database
        connection = mariadb.connect(
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            database=DATABASE
        )
        cursor = connection.cursor()

        for station in ground_stations:
            # Check if the ground station already exists by its name
            cursor.execute(
                "SELECT COUNT(*) FROM GroundStation WHERE name = ?",
                (station.name,)
            )
            exists = cursor.fetchone()[0] > 0

            if exists:
                # Update the existing ground station
                cursor.execute(
                    """
                    UPDATE GroundStation
                    SET latitude = ?, longitude = ?, altitude = ?, 
                        start_tracking_elevation = ?, is_active = ?
                    WHERE name = ?
                    """,
                    (
                        station.latitude, station.longitude, station.altitude,
                        station.start_tracking_elevation, station.is_active,
                        station.name
                    )
                )
                print(f"Updated ground station: {station.name}")
            else:
                # Insert a new ground station
                cursor.execute(
                    """
                    INSERT INTO GroundStation 
                    (name, latitude, longitude, altitude, start_tracking_elevation, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        station.name, station.latitude, station.longitude,
                        station.altitude, station.start_tracking_elevation,
                        station.is_active
                    )
                )
                print(f"Inserted new ground station: {station.name}")

        # Commit the changes
        connection.commit()

    except mariadb.Error as e:
        print(f"Error saving ground stations to database: {e}")
    finally:
        if connection:
            connection.close()

def fetch_ground_stations(api_url):
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()

        # Parse the response into GroundStation objects
        ground_stations = [
            GroundStation(
                name=item['name'],
                latitude=item['latitude'],
                longitude=item['longitude'],
                altitude=item['altitude'],
                start_tracking_elevation=item['start_tracking_elevation'],
                is_active=item['is_active'],
            )
            for item in data
        ]
        return ground_stations
    except requests.RequestException as e:
        print(f"Error fetching ground stations: {e}")
        return []

def get_ground_stations(api_url):
    # Try to fetch ground stations from the API
    ground_stations = fetch_ground_stations(api_url)

    if ground_stations:
        # If we have a valid response, save it to the database
        save_ground_stations_to_db(ground_stations)
    else:
        # If the API fails, fetch ground stations from the database
        try:
            connection = mariadb.connect(
                user=DATABASE_USER,
                password=DATABASE_PASSWORD,
                host=DATABASE_HOST,
                database=DATABASE
            )
            cursor = connection.cursor()

            # Retrieve all ground stations from the database
            cursor.execute(
                "SELECT name, latitude, longitude, altitude, start_tracking_elevation, is_active FROM GroundStation")
            rows = cursor.fetchall()

            ground_stations = [
                GroundStation(
                    name=row[0],
                    latitude=row[1],
                    longitude=row[2],
                    altitude=row[3],
                    start_tracking_elevation=row[4],
                    is_active=row[5],
                )
                for row in rows
            ]
            print("Fetched ground stations from the database.")
            return ground_stations

        except mariadb.Error as e:
            print(f"Error fetching ground stations from database: {e}")
            return []
        finally:
            if connection:
                connection.close()

    return ground_stations
