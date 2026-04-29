from dataclasses import dataclass


@dataclass
class SimulationStats:
    total_vehicles: int = 0
    total_crossings: int = 0
    total_collisions: int = 0
