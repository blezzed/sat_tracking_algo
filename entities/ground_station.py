
class GroundStation:
    def __init__(self, name, latitude, longitude, altitude, start_tracking_elevation, is_active):
        self.name = name
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.altitude = float(altitude)
        self.start_tracking_elevation = float(start_tracking_elevation)
        self.is_active = is_active

    def __str__(self):
        return f"{self.name} - Lat: {self.latitude}, Lon: {self.longitude}, Alt: {self.altitude}m"
