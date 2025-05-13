import requests
import datetime

# Replace with your API URL
API_URL = "http://127.0.0.1:8001/api/telemetry/"


# Function to send telemetry data
def send_telemetry():
    # Replace these with actual data from your Raspberry Pi sensors
    telemetry_data = {
        "satellite_id": 1,  # Replace with the appropriate satellite ID
        "timestamp": datetime.datetime.now().isoformat(),
        "latitude": -29.81,
        "longitude": 51.23,
        "altitude": 997.44,
        "battery_voltage": 3.96,
        "command_status": "Idle",
        "data_rate": 3.88,
        "health_status": "Nominal",
        "temperature": 14.83,
        "velocity": 7.9,
        "power_consumption": 190.83,
        "solar_panel_status": True,
        "error_code": None,
        "yaw": -130.24,
        "roll": 135.99,
        "pitch": -6.23,
        "signal_strength": -71.82,
    }

    try:
        # Send POST request
        response = requests.post(API_URL, json=telemetry_data)

        # Check if the request was successful
        if response.status_code == 201:  # HTTP 201 Created
            print("Telemetry data successfully sent!")
            print("Response:", response.json())
        else:
            print("Failed to send telemetry data.")
            print("Status Code:", response.status_code)
            print("Response:", response.json())
    except requests.RequestException as e:
        print("Error while sending telemetry data:", e)
