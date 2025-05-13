
"""
database.py

Module for persisting and retrieving satellite TLE and ground station data
in a MariaDB database, with API fallback for ground station retrieval.
"""
import mariadb  # MariaDB connector for Python
import requests  # HTTP library for fetching ground station data

# Entity definitions for structured data handling
from entities.ground_station import GroundStation
from entities.sat_tle import SatelliteTLE

# Database credentials and connection values
from values import DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE


def save_satellites_to_db(satellites):
    """
    Insert or update a list of SatelliteTLE entities in the database.

    Args:
        satellites (List[SatelliteTLE]): Satellite TLE data to save.
    """
    try:
        # 1. Establish a connection to the MariaDB database
        connection = mariadb.connect(
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            database=DATABASE
        )
        cursor = connection.cursor()

        # 2. Iterate over each satellite entity
        for satellite in satellites:
            # Check if this satellite already exists by name
            cursor.execute(
                "SELECT COUNT(*) FROM SatelliteTLE WHERE name = ?",
                (satellite.name,)
            )
            exists = cursor.fetchone()[0] > 0

            if exists:
                # Update existing record if present
                cursor.execute(
                    """
                    UPDATE SatelliteTLE
                    SET line1 = ?, line2 = ?, tle_group = ?, auto_tracking = ?, 
                        orbit_status = ?, last_updated = ?
                    WHERE name = ?
                    """,
                    (
                        satellite.line1,
                        satellite.line2,
                        satellite.tle_group,
                        satellite.auto_tracking,
                        satellite.orbit_status,
                        satellite.last_updated,
                        satellite.name
                    )
                )
                print(f"Updated satellite: {satellite.name}")
            else:
                # Insert new record when satellite does not exist
                cursor.execute(
                    """
                    INSERT INTO SatelliteTLE 
                    (name, line1, line2, tle_group, auto_tracking, orbit_status, created_at, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        satellite.name,
                        satellite.line1,
                        satellite.line2,
                        satellite.tle_group,
                        satellite.auto_tracking,
                        satellite.orbit_status,
                        satellite.created_at,
                        satellite.last_updated
                    )
                )
                print(f"Inserted new satellite: {satellite.name}")

        # 3. Commit all changes to the database
        connection.commit()

    except mariadb.Error as e:
        # Handle any database errors
        print(f"Error saving satellites to database: {e}")
    finally:
        # Ensure the connection is closed
        if 'connection' in locals():
            connection.close()


def get_all_satellites_from_db():
    """
    Retrieve all orbiting and auto-tracking SatelliteTLE records from the database.

    Returns:
        List[SatelliteTLE]: List of SatelliteTLE entities.
    """
    satellites = []
    try:
        # Open a database connection
        connection = mariadb.connect(
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            database=DATABASE
        )
        cursor = connection.cursor()

        # Query only orbiting satellites marked for auto-tracking
        cursor.execute(
            """
            SELECT name, line1, line2, tle_group, auto_tracking, orbit_status, created_at, last_updated
            FROM SatelliteTLE
            WHERE orbit_status = 'orbiting' AND auto_tracking = TRUE
            """
        )

        # Convert each row into a SatelliteTLE entity
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
        # Close connection if open
        if 'connection' in locals():
            connection.close()

    return satellites


def save_ground_stations_to_db(ground_stations):
    """
    Insert or update GroundStation entities in the database.

    Args:
        ground_stations (List[GroundStation]): Ground station data to save.
    """
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
            # Check existence by station name
            cursor.execute(
                "SELECT COUNT(*) FROM GroundStation WHERE name = ?",
                (station.name,)
            )
            exists = cursor.fetchone()[0] > 0

            if exists:
                # Update existing record
                cursor.execute(
                    """
                    UPDATE GroundStation
                    SET latitude = ?, longitude = ?, altitude = ?, 
                        start_tracking_elevation = ?, is_active = ?
                    WHERE name = ?
                    """,
                    (
                        station.latitude,
                        station.longitude,
                        station.altitude,
                        station.start_tracking_elevation,
                        station.is_active,
                        station.name
                    )
                )
                print(f"Updated ground station: {station.name}")
            else:
                # Insert new station
                cursor.execute(
                    """
                    INSERT INTO GroundStation 
                    (name, latitude, longitude, altitude, start_tracking_elevation, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        station.name,
                        station.latitude,
                        station.longitude,
                        station.altitude,
                        station.start_tracking_elevation,
                        station.is_active
                    )
                )
                print(f"Inserted new ground station: {station.name}")

        # Commit changes
        connection.commit()

    except mariadb.Error as e:
        print(f"Error saving ground stations to database: {e}")
    finally:
        if 'connection' in locals():
            connection.close()


def fetch_ground_stations(api_url):
    """
    Fetch ground station definitions from a remote API.

    Args:
        api_url (str): Endpoint URL returning JSON station data.

    Returns:
        List[GroundStation]: Parsed ground station entities, or empty list on failure.
    """
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        # Parse each JSON item into a GroundStation entity
        return [
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
    except requests.RequestException as e:
        print(f"Error fetching ground stations: {e}")
        return []


def get_ground_stations(api_url):
    """
    Retrieve ground stations via API; if unavailable, fall back to database.

    Args:
        api_url (str): Endpoint for fetching ground station data.

    Returns:
        List[GroundStation]: Active ground station entities.
    """
    # Attempt API fetch
    ground_stations = fetch_ground_stations(api_url)

    if ground_stations:
        # Save new/updated stations to database
        save_ground_stations_to_db(ground_stations)
    else:
        # Fallback: read from local database
        try:
            connection = mariadb.connect(
                user=DATABASE_USER,
                password=DATABASE_PASSWORD,
                host=DATABASE_HOST,
                database=DATABASE
            )
            cursor = connection.cursor()
            cursor.execute(
                "SELECT name, latitude, longitude, altitude, start_tracking_elevation, is_active FROM GroundStation"
            )
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
        except mariadb.Error as e:
            print(f"Error fetching ground stations from database: {e}")
            ground_stations = []
        finally:
            if 'connection' in locals():
                connection.close()

    return ground_stations
