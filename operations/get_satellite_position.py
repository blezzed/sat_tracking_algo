from skyfield.api import wgs84, load, EarthSatellite
from datetime import datetime, timedelta
import time
import RPi.GPIO as GPIO
import pytz

from repo.api import fetch_and_parse_satellite_data
from values import API_URL_GROUND_STATIONS, API_URL_SATELLITES, AZIMUTH_PIN, ELEVATION_PIN


# Cleanup function to stop PWM and clean GPIO pins
def cleanup():
    GPIO.cleanup()

def set_angle(pwm, angle):
    # Map the angle to a duty cycle (1ms to 2ms)
    duty = (angle / 18) + 2
    pwm.ChangeDutyCycle(duty)

def adjust_azimuth_elevation(azimuth, elevation, azimuth_pwm, elevation_pwm):
    # If azimuth is greater than 180°, rotate back to 1° and adjust elevation accordingly
    print(f"Adjusting to azimuth {azimuth}° and elevation {elevation}° ")
    if azimuth > 180:
        azimuth = azimuth % 180
        # Invert elevation based on 90° midpoint
        elevation = 90 - (elevation - 90)
    
    # Map azimuth and elevation to appropriate angles for the servos
    elevation -= 5
    set_angle(azimuth_pwm, azimuth)
    set_angle(elevation_pwm, elevation)

def satellite_Elv_Azm(gs, satellite, azimuth_pwm, elevation_pwm):
    ts = load.timescale()
    t = ts.now()

    #gs = fetch_ground_stations(API_URL_GROUND_STATIONS)[0]

    ground_station = wgs84.latlon(gs.latitude, gs.longitude)

    difference = satellite - ground_station

    topo_centric = difference.at(t)
    alt, az, distance = topo_centric.altaz()

    print(f"Elv: {round(alt.degrees, 1)}° Azm: {round(az.degrees, 1)}°")
    
    adjust_azimuth_elevation(az.degrees, alt.degrees, azimuth_pwm, elevation_pwm)
    
    return alt.degrees


def satellite_position(gs):
    """
    Get the position of all satellites and move the servos to track the closest satellite.
    """
    
    ts = load.timescale()
    t = ts.now()

    #gs = fetch_ground_stations(API_URL_GROUND_STATIONS)[0]

    ground_station = wgs84.latlon(gs.latitude, gs.longitude)

    # Fetch TLE data from the database
    tle_data = fetch_and_parse_satellite_data(API_URL_SATELLITES)

    print("-----------------------------------------------------------------------")
    print("SATELLITE POSITION")

    # List to store the positions of all satellites
    satellite_positions = []

    for tle in tle_data:
        satellite = EarthSatellite(tle.line1, tle.line2, tle.name, ts)
        geocentric = satellite.at(t)

        lat, lon = wgs84.latlon_of(geocentric)

        difference = satellite - ground_station

        topo_centric = difference.at(t)
        alt, az, distance = topo_centric.altaz()

        if alt.degrees > 10 and tle.is_auto_tracking_enabled() == True and tle.orbit_status == "orbiting":
            print("-----------------------------------------------------------------------")
            print(f'{satellite.name}'.upper())
            print("IS ABOVE THE HORIZON")
            print("-----------------------------------------------------------------------")
            
            # Setup for controlling servos
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(AZIMUTH_PIN, GPIO.OUT)
            GPIO.setup(ELEVATION_PIN, GPIO.OUT)

            # Set PWM frequency (50Hz for standard servos)
            azimuth_pwm = GPIO.PWM(AZIMUTH_PIN, 50)
            elevation_pwm = GPIO.PWM(ELEVATION_PIN, 50)

            azimuth_pwm.start(0)  # Initialize PWM for azimuth servo
            elevation_pwm.start(0)  # Initialize PWM for elevation servo

            while alt.degrees > 10:
                alt.degrees = satellite_Elv_Azm(gs, satellite, azimuth_pwm, elevation_pwm)
                time.sleep(2)
                
            # Call cleanup function when exiting the program
            adjust_azimuth_elevation(0, 0, azimuth_pwm, elevation_pwm)
            azimuth_pwm.stop()
            elevation_pwm.stop()
            cleanup()

        # Create an object for the satellite's position with all the necessary details
        satellite_info = {
            "name": satellite.name,
            "elevation": round(alt.degrees, 1),
            "azimuth": round(az.degrees, 1),
            "distance_km": round(distance.km, 1),
            "latitude": lat.degrees,
            "longitude": lon.degrees
        }

        print(
            f"Satellite: {satellite_info['name']} ----- Elv: {satellite_info['elevation']}° Azm: {satellite_info['azimuth']}° distance: {satellite_info['distance_km']} km ===> lat: {satellite_info['latitude']} lon: {satellite_info['longitude']}")

        # Append the satellite info object to the list
        satellite_positions.append(satellite_info)

    # Sort the list by distance (closest satellite first)
    satellite_positions.sort(key=lambda x: x['distance_km'])

    return satellite_positions




