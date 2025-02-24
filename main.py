import asyncio
from datetime import datetime, timedelta
import pytz
import RPi.GPIO as GPIO
import time

from operations.get_satellite_passes import get_satellite_passes 
from operations.get_satellite_position import satellite_position  # Function to get satellite positions
from repo.api import fetch_and_parse_satellite_data
from repo.database import get_ground_stations
from values import API_URL_GROUND_STATIONS


def sort_satellite_passes(decodedData):
    """
    Sort satellite passes based on their event time.
    """
    # Step 1: Flatten the data into a single list
    all_passes = []
    for satellite, passes in decodedData.items():
        for sat_pass in passes:
            # Add the satellite name to each pass for reference
            sat_pass['satellite'] = satellite
            all_passes.append(sat_pass)

    # Step 2: Convert 'event_time' to datetime objects for sorting
    for sat_pass in all_passes:
        sat_pass['event_time'] = datetime.strptime(sat_pass['event_time'], '%Y-%m-%d %H:%M:%S')

    # Step 3: Sort the list by 'event_time'
    sorted_passes = sorted(all_passes, key=lambda x: x['event_time'])

    # Step 4: Convert 'event_time' back to string for JSON serialization
    for sat_pass in sorted_passes:
        sat_pass['event_time'] = sat_pass['event_time'].strftime('%Y-%m-%d %H:%M:%S')

    return sorted_passes


async def main():
    while True:
        # Fetch the first ground station from the API
        gs = get_ground_stations(API_URL_GROUND_STATIONS)[0]

        # Load satellite passes from the external source
        satellite_passes_data = get_satellite_passes(gs)
        #print(f'SATELLITE PASSES SUCCESSFULLY LOADED: {satellite_passes_data}')

        # Initialize variables for the next satellite pass events
        next_rise = None
        next_set = None
        culminate_event = None
        now = datetime.now(pytz.timezone('Africa/Maputo')).astimezone(pytz.utc) + timedelta(hours=2)

        # Iterate through satellite passes to find the next rise and set events
        for satellite, passes in satellite_passes_data.items():
            rise_event = None
            set_event = None
            for sat_pass in passes:
                event_time_str = sat_pass['event_time']
                # Convert the string to a datetime object
                event_time = datetime.strptime(event_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)

                # Find the next 'Satellite Rise' event
                if sat_pass['event'] == 'Satellite Rise' and event_time > now:
                    rise_event = {
                        'event_time': event_time,  # Save as datetime object
                        'pass_data': sat_pass
                    }

                # Find the culmination event (highest elevation)
                if rise_event and sat_pass['event'] == 'culminate' and event_time > rise_event['event_time']:
                    culminate_event = {
                        'event_time': event_time,  # Save as datetime object
                        'pass_data': sat_pass
                    }

                # Find the 'Satellite Set' event for the same pass
                if rise_event and sat_pass['event'] == 'Satellite Set' and event_time > rise_event['event_time']:
                    set_event = {
                        'event_time': event_time,  # Save as datetime object
                        'pass_data': sat_pass
                    }
                    break

            # Update the next rise and set events if found
            if rise_event and set_event:
                rise_time = rise_event['event_time']
                if next_rise is None or rise_time < next_rise['event_time']:
                    next_rise = {
                        'satellite': satellite,
                        'event_time': rise_time,
                        'pass_data': rise_event
                    }
                    next_set = {
                        'satellite': satellite,
                        'event_time': set_event['event_time'],
                        'pass_data': set_event
                    }

        # Handle the case where no events are found
        if not next_rise or not next_set:
            print("No upcoming satellite passes found.")
            await asyncio.sleep(60)  # Wait for 1 minute before trying again
            continue

        # Calculate time until the next pass
        now = datetime.now(pytz.timezone('Africa/Maputo')).astimezone(pytz.utc) + timedelta(hours=2)
        time_until_pass = (next_rise['event_time'] - now).total_seconds()
        time_until_wake = time_until_pass - (2 * 60)  # Wake 2 minutes before the pass

        if time_until_wake > 0:
            print(
                f"Sleeping {time_until_wake / 60:.2f} minutes until 2 minutes before the pass of {next_rise['satellite']} at {next_rise['event_time']}")
            await asyncio.sleep(time_until_wake)

        # Track satellite position until the pass is over
        while True:
            position = satellite_position(gs)
            # Check if the satellite is above the minimum tracking elevation
            satelliteInHorizon = next((s for s in position if s['name'] == next_rise['satellite']), None)
            
            now = datetime.now(pytz.timezone('Africa/Maputo')).astimezone(pytz.utc) + timedelta(hours=2) 
            time_until_pass = (next_rise['event_time'] - now).total_seconds()
            print(time_until_pass)
        
            if satelliteInHorizon['elevation'] < gs.start_tracking_elevation and time_until_pass < 0:
                break
            await asyncio.sleep(4)

        # Sleep until 30 seconds after the pass ends
        now = datetime.now(pytz.timezone('Africa/Maputo')).astimezone(pytz.utc) + timedelta(hours=2) 
        time_until_after_set = (next_set['event_time'] - now).total_seconds() + 30
        if time_until_after_set > 0:
            print(
                f"Sleeping {time_until_after_set / 60:.2f} minutes until after the pass of {next_rise['satellite']} ends at {next_set['event_time']}")
            await asyncio.sleep(time_until_after_set)

        # Notify the user that the pass has ended
        print(f"30 seconds has passed since the pass of {next_rise['satellite']} ended at {next_set['event_time']}")

        await asyncio.sleep(1)  # Prevent tight loops


if __name__ == '__main__':
    
    asyncio.run(main())
