# sat\_tracking\_algo

An asynchronous Raspberry Pi-based satellite tracking system: fetches TLE data, computes upcoming passes, and drives servos to follow satellites in real time.

## Features

* **Automated TLE ingestion** from remote API with local database fallback
* **Pass prediction** over a two‑day horizon using Skyfield
* **Real‑time position updates** with topocentric calculations (altitude, azimuth, slant range)
* **GPIO servo control** for azimuth & elevation pointing
* **Configurable ground stations**: fetch via API or database
* **Graceful error handling** and logging

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Project Structure](#project-structure)
6. [Contributing](#contributing)
7. [License](#license)

## Prerequisites

* Python 3.10+ 
* `pip` package manager
* MariaDB or MySQL server
* Raspberry Pi with GPIO headers (for servo control)

## Installation

1. Clone the repository:

   ```bash
   git clone git@github.com:blezzed/sat_tracking_algo.git
   cd sat_tracking_algo
   ```
2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
4. Ensure MariaDB is running and credentials match `values.py` settings.

## Configuration

Edit `values.py` to set:

* `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE` for MariaDB connection
* `API_URL_SATELLITES`, `API_URL_GROUND_STATIONS` endpoints
* `AZIMUTH_PIN`, `ELEVATION_PIN` GPIO pin numbers

## Usage

1. Initialize the database schema (run your SQL migration or create tables):

   ```sql
   CREATE TABLE SatelliteTLE (...);
   CREATE TABLE GroundStation (...);
   ```
2. Start the main tracking loop:

   ```bash
   python main.py
   ```
3. Console logs will report fetch status, upcoming passes, and servo movements.

## Project Structure

```
├── main.py                   # Core async loop: fetch passes & trigger tracking
├── operations/
│   ├── get_satellite_passes.py   # Compute rise/culmination/set events
│   └── get_satellite_position.py # Real‑time topocentric position & servo control
├── repo/
│   ├── api.py                 # TLE & ground station fetch + parse + db persistence
│   └── database.py            # Database CRUD for satellites & stations
├── entities/                  # Data classes: GroundStation, SatelliteTLE
├── values.py                  # Configuration constants
├── requirements.txt           # Python dependencies
└── README.md                  # Project overview & instructions
```

## Contributing

1. Fork the repo
2. Create a feature branch
3. Submit a pull request

## License

MIT License. See [LICENSE](LICENSE) for details.
