
"""
get_satellite_position.py

Module to compute real-time satellite topocentric positions for a ground station,
control GPIO-driven servos for azimuth and elevation tracking, and return
a sorted list of all visible satellites by distance.
"""
# Standard and third-party imports
from skyfield.api import wgs84, load, EarthSatellite  # for satellite and geodetic computations
from datetime import datetime, timedelta
import time  # for sleep delays during servo polling
import RPi.GPIO as GPIO  # Raspberry Pi GPIO interface for servo control
import pytz  # timezone handling

# Local API and constants
from repo.api import fetch_and_parse_satellite_data  # fetch TLE data
from values import API_URL_GROUND_STATIONS, API_URL_SATELLITES, AZIMUTH_PIN, ELEVATION_PIN


def cleanup():
    """
    Reset and free GPIO pins when finished tracking or on exit.
    """
    GPIO.cleanup()


def set_angle(pwm, angle):
    """
    Convert a desired servo angle into a PWM duty cycle and apply it.

    Args:
        pwm: GPIO.PWM instance controlling a servo channel
        angle (float): Desired servo angle in degrees (0–180)
    """
    # Typical servo: 1ms pulse (0°) to 2ms pulse (180°) at 50Hz (20ms period)
    duty = (angle / 18.0) + 2.0
    pwm.ChangeDutyCycle(duty)


def adjust_azimuth_elevation(azimuth, elevation, azimuth_pwm, elevation_pwm):
    """
    Normalize and map raw azimuth/elevation angles to servo-safe limits,
    then update both azimuth and elevation servos.

    Args:
        azimuth (float): Raw compass bearing (deg, 0–360)
        elevation (float): Raw elevation angle (deg, 0–90)
        azimuth_pwm: Servo PWM for azimuth
        elevation_pwm: Servo PWM for elevation
    """
    print(f"Adjusting to azimuth {azimuth:.1f}° and elevation {elevation:.1f}°")

    # Wrap-around: if azimuth > 180°, map into 0–180 range for servo rotation
    if azimuth > 180.0:
        azimuth = azimuth - 180.0
        # Mirror elevation around 90° to keep servo within safe travel
        elevation = 90.0 - (elevation - 90.0)

    # Apply a small downward offset so servo starts from level
    elevation = max(0.0, elevation - 5.0)

    # Command servos to new positions
    set_angle(azimuth_pwm, azimuth)
    set_angle(elevation_pwm, elevation)


def satellite_elv_azm(gs, satellite, az_pwm, el_pwm):  # renamed for clarity
    """
    Update servos to track a single satellite at current time.

    Args:
        gs: Ground station object with latitude/longitude
        satellite: EarthSatellite instance to track
        az_pwm: Azimuth servo PWM instance
        el_pwm: Elevation servo PWM instance

    Returns:
        float: Current elevation (deg) for loop continuation check
    """
    # Load current timestamp for skyfield
    ts = load.timescale()
    t = ts.now()

    # Define topocentric observer location
    ground = wgs84.latlon(gs.latitude, gs.longitude)

    # Compute line-of-sight vector and its alt/az
    topo = (satellite - ground).at(t)
    alt, az, _ = topo.altaz()

    # Print current pointing angles
    print(f"Elv: {alt.degrees:.1f}° Azm: {az.degrees:.1f}°")

    # Move servos to point at satellite
    adjust_azimuth_elevation(az.degrees, alt.degrees, az_pwm, el_pwm)
    return alt.degrees


def satellite_position(gs):
    """
    Fetch current positions for all TLE satellites, move servos to
    continuously track the closest one above horizon, and
    return a sorted list of all satellite position dicts.

    Args:
        gs: Ground station object with attributes latitude, longitude,
            and start_tracking_elevation (minimum elevation deg).

    Returns:
        list of dict: Each dict contains name, elevation, azimuth,
                      distance_km, latitude, longitude.
    """
    # Initialize skyfield
    ts = load.timescale()
    t = ts.now()

    # Observer location for topocentric transforms
    ground = wgs84.latlon(gs.latitude, gs.longitude)

    # Retrieve TLE list from API
    tle_list = fetch_and_parse_satellite_data(API_URL_SATELLITES)

    print("-----------------------------------------------------------------------")
    print("SATELLITE POSITION QUERY")

    positions = []  # Collect all satellites' info

    # Iterate and compute position for each satellite
    for tle in tle_list:
        sat = EarthSatellite(tle.line1, tle.line2, tle.name, ts)
        # Geocentric lat/lon (not strictly needed for tracking)
        geo = sat.at(t)
        lat, lon = wgs84.latlon_of(geo)

        # Topocentric transform for alt/az/distance
        topo = (sat - ground).at(t)
        alt, az, dist = topo.altaz()

        # If this satellite is in view, auto-tracking enabled, and orbiting, engage servos
        if (alt.degrees > gs.start_tracking_elevation and
            tle.is_auto_tracking_enabled() and
            tle.orbit_status == "orbiting"):

            print(f"Tracking {sat.name} above horizon at {alt.degrees:.1f}° elevation.")

            # GPIO setup for servos
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(AZIMUTH_PIN, GPIO.OUT)
            GPIO.setup(ELEVATION_PIN, GPIO.OUT)

            # Instantiate PWM channels at 50Hz
            az_pwm = GPIO.PWM(AZIMUTH_PIN, 50)
            el_pwm = GPIO.PWM(ELEVATION_PIN, 50)
            az_pwm.start(0)
            el_pwm.start(0)

            # Continuously adjust servos while satellite remains above minimum elevation
            while True:
                current_alt = satellite_elv_azm(gs, sat, az_pwm, el_pwm)
                # Break loop once satellite dips below threshold
                if current_alt <= gs.start_tracking_elevation:
                    break
                time.sleep(2)

            # Reset servos to home position and cleanup
            adjust_azimuth_elevation(0.0, 0.0, az_pwm, el_pwm)
            az_pwm.stop()
            el_pwm.stop()
            cleanup()

        # Build position record for this satellite
        info = {
            "name": sat.name,
            "elevation": round(alt.degrees, 1),
            "azimuth": round(az.degrees, 1),
            "distance_km": round(dist.km, 1),
            "latitude": lat.degrees,
            "longitude": lon.degrees
        }
        print(f"{info['name']}: Elv {info['elevation']}° Azm {info['azimuth']}° Distance {info['distance_km']} km Lat {info['latitude']:.3f} Lon {info['longitude']:.3f}")

        positions.append(info)

    # Sort by slant range so closest satellites come first
    positions.sort(key=lambda x: x['distance_km'])
    return positions
