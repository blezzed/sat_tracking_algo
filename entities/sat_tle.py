from datetime import datetime, timezone
from dateutil.parser import isoparse


class SatelliteTLE:
    def __init__(self, name, line1, line2, tle_group, auto_tracking, orbit_status, created_at, last_updated):
        self.name = name
        self.line1 = line1
        self.line2 = line2
        self.tle_group = tle_group
        self.auto_tracking = auto_tracking
        self.orbit_status = orbit_status
        self.created_at = isoparse(created_at) if created_at else None
        self.last_updated = isoparse(last_updated) if last_updated else None

    def __str__(self):
        return f"Satellite {self.name} - Group: {self.tle_group}, Status: {self.orbit_status}"

    def is_auto_tracking_enabled(self):
        return self.auto_tracking

    def time_since_last_update(self):
        now = datetime.now(timezone.utc)  # Assuming the API timestamps are in UTC
        delta = now - self.last_updated
        return delta.days
