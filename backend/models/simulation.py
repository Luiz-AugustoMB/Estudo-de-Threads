from dataclasses import dataclass


@dataclass
class SimulationStats:
    total_cars: int = 0
    active_cars: int = 0
    finished_cars: int = 0
    collisions: int = 0
