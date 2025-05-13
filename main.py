#!/usr/bin/env python3
"""
main.py

Asynchronous script running on a Raspberry Pi to:
 1. Fetch ground station data and upcoming satellite passes.
 2. Identify the next pass (rise, culmination, set) for satellites.
 3. Sleep until 2 minutes before the next rise event.
 4. Track the satellite while above horizon and until the pass ends.
 5. Notify user via console prints when passes start and end.
"""
import asyncio
from datetime import datetime, timedelta
import pytz
import RPi.GPIO as GPIO  # Unused in this snippet, likely for GPIO notifications
import time

from operations.get_satellite_passes import get_satellite_passes
from operations.get_satellite_position import satellite_position
from repo.api import fetch_and_parse_satellite_data  # Imported but not used in this file
from repo.database import get_ground_stations
from values import API_URL_GROUND_STATIONS


def sort_satellite_passes(decodedData):
    """
    Flatten and sort a dictionary of satellite pass events by event_time.

    Args:
        decodedData (dict): Keys are satellite names, values are lists of pass dicts
            Each pass dict contains 'event_time' (str) and other pass info.

    Returns:
        list: Sorted list of all pass dicts with 'satellite' key added.
    """
    # Step 1: Flatten the data into a single list
    all_passes = []
    for satellite, passes in decodedData.items():
        for sat_pass in passes:
            sat_pass['satellite'] = satellite  # Annotate each pass with its satellite
            all_passes.append(sat_pass)

    # Step 2: Parse event_time strings into datetime objects
    for sat_pass in all_passes:
        sat_pass['event_time'] = datetime.strptime(
            sat_pass['event_time'], '%Y-%m-%d %H:%M:%S'
        )

    # Step 3: Sort passes by their datetime
    sorted_passes = sorted(all_passes, key=lambda x: x['event_time'])

    # Step 4: Convert datetimes back into strings for serialization
    for sat_pass in sorted_passes:
        sat_pass['event_time'] = sat_pass['event_time'].strftime('%Y-%m-%d %H:%M:%S')

    return sorted_passes


async def main():
    """
    Main loop:
      - Fetch first ground station
      - Retrieve upcoming passes for that station
      - Find the next rise and set events
      - Sleep until 2 min before rise
      - Track satellite position during the pass
      - Notify when pass ends
      - Repeat indefinitely
    """
    while True:
        # Get ground station configuration (assume first in list)
        gs = get_ground_stations(API_URL_GROUND_STATIONS)[0]

        # Fetch upcoming passes from an external source
        satellite_passes_data = get_satellite_passes(gs)
        # print(f'SATELLITE PASSES SUCCESSFULLY LOADED: {satellite_passes_data}')

        # Initialize placeholders for the next events
        next_rise = None
        next_set = None
        culminate_event = None

        # Current time in UTC (adjusted from Africa/Maputo local)
        now = datetime.now(pytz.timezone('Africa/Maputo')).astimezone(pytz.utc) + timedelta(hours=2)

        # Iterate over each satellite to find its next pass events
        for satellite, passes in satellite_passes_data.items():
            rise_event = None
            set_event = None

            for sat_pass in passes:
                # Parse each event's timestamp
                event_time = datetime.strptime(
                    sat_pass['event_time'], '%Y-%m-%d %H:%M:%S'
                ).replace(tzinfo=pytz.utc)

                # Identify the next rise event after now
                if sat_pass['event'] == 'Satellite Rise' and event_time > now:
                    rise_event = {
                        'event_time': event_time,
                        'pass_data': sat_pass
                    }

                # Identify culmination (highest elevation) after rise
                if rise_event and sat_pass['event'] == 'culminate' and event_time > rise_event['event_time']:
                    culminate_event = {
                        'event_time': event_time,
                        'pass_data': sat_pass
                    }

                # Identify the set event after rise, then break (end of pass)
                if rise_event and sat_pass['event'] == 'Satellite Set' and event_time > rise_event['event_time']:
                    set_event = {
                        'event_time': event_time,
                        'pass_data': sat_pass
                    }
                    break

            # If we found a full pass, update global next_rise/next_set if earlier
            if rise_event and set_event:
                if next_rise is None or rise_event['event_time'] < next_rise['event_time']:
                    next_rise = {
                        'satellite': satellite,
                        'event_time': rise_event['event_time'],
                        'pass_data': rise_event
                    }
                    next_set = {
                        'satellite': satellite,
                        'event_time': set_event['event_time'],
                        'pass_data': set_event
                    }

        # If no valid upcoming passes were found, wait and retry
        if not next_rise or not next_set:
            print("No upcoming satellite passes found.")
            await asyncio.sleep(60)
            continue

        # Recalculate current time before computing sleep duration
        now = datetime.now(pytz.timezone('Africa/Maputo')).astimezone(pytz.utc) + timedelta(hours=2)
        time_until_pass = (next_rise['event_time'] - now).total_seconds()
        time_until_wake = time_until_pass - (2 * 60)  # Wake 2 minutes before rise

        # Sleep until it's time to start tracking
        if time_until_wake > 0:
            print(
                f"Sleeping {time_until_wake / 60:.2f} minutes until 2 minutes before the pass of"
                f" {next_rise['satellite']} at {next_rise['event_time']}"
            )
            await asyncio.sleep(time_until_wake)

        # Active tracking loop: poll satellite position until pass is over
        while True:
            position = satellite_position(gs)  # Get current satellite positions
            # Find this satellite's current elevation
            satelliteInHorizon = next(
                (s for s in position if s['name'] == next_rise['satellite']),
                None
            )

            # Update current time
            now = datetime.now(pytz.timezone('Africa/Maputo')).astimezone(pytz.utc) + timedelta(hours=2)
            time_until_pass = (next_rise['event_time'] - now).total_seconds()
            print(time_until_pass)

            # Exit tracking once the satellite drops below horizon after the pass
            if (
                satelliteInHorizon and
                satelliteInHorizon['elevation'] < gs.start_tracking_elevation
                and time_until_pass < 0
            ):
                break

            await asyncio.sleep(4)  # Poll every 4 seconds

        # Sleep until 30 seconds after the set event
        now = datetime.now(pytz.timezone('Africa/Maputo')).astimezone(pytz.utc) + timedelta(hours=2)
        time_until_after_set = (next_set['event_time'] - now).total_seconds() + 30
        if time_until_after_set > 0:
            print(
                f"Sleeping {time_until_after_set / 60:.2f} minutes until after the pass of"
                f" {next_rise['satellite']} ends at {next_set['event_time']}"
            )
            await asyncio.sleep(time_until_after_set)

        # Notify that the pass has fully ended
        print(
            f"30 seconds has passed since the pass of {next_rise['satellite']} ended at {next_set['event_time']}"
        )

        await asyncio.sleep(1)  # Short pause before next iteration


if __name__ == '__main__':
    # Start the asynchronous main loop
    asyncio.run(main())
