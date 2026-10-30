from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class Settings:
    seed: int = 20261022
    start_date: date = date(2026, 1, 5)
    road_distance_factor: float = 1.25
    average_speed_kmh: float = 25.0
    stop_dwell_minutes: int = 2
    service_radius_km: float = 15.0
    pickup_grace_minutes: int = 10
    max_route_duration_minutes: int = 240
    absence_probability: float = 0.04
    disruption_probability: float = 0.025

STARTER = {"students": 250, "buses": 10, "stops": 30, "school_days": 10}
FULL = {"students": 5000, "buses": 100, "stops": 300, "school_days": 200}
