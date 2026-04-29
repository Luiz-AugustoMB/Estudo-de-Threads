from dataclasses import dataclass
from enum import Enum
import time


class CarState(str, Enum):
    MOVING = "moving"
    WAITING = "waiting"
    IN_CRITICAL = "in_critical"
    COLLIDED = "collided"
    FINISHED = "finished"


class Direction(str, Enum):
    NORTH = "north"
    SOUTH = "south"
    WEST = "west"
    EAST = "east"


class VehicleType(str, Enum):
    CAR = "car"
    TRUCK = "truck"


@dataclass
class Car:
    id: int
    direction: Direction
    vehicle_type: VehicleType
    x: float
    y: float
    speed: float
    lane_coord: float
    stagger: float = 0.0

    state: CarState = CarState.MOVING
    quadrant: str = ""
    crossings: int = 0

    crossing_start: float = 0.0
    last_crossing_time: float = 0.0
    final_time: float = 0.0
    total_wait_time: float = 0.0
    waiting_since: float = 0.0

    def to_dict(self) -> dict:
        now = time.time()
        total_time = None
        if self.crossing_start > 0:
            total_time = (
                round(self.final_time, 2)
                if self.final_time > 0
                else round(now - self.crossing_start, 2)
            )

        wait_time = self.total_wait_time
        if self.waiting_since > 0:
            wait_time += now - self.waiting_since

        return {
            "id": self.id,
            "direction": self.direction.value,
            "vehicle_type": self.vehicle_type.value,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "speed": self.speed,
            "state": self.state.value,
            "quadrant": self.quadrant,
            "crossings": self.crossings,
            "total_time": total_time,
            "wait_time": round(wait_time, 2),
            "last_crossing_time": (
                round(self.last_crossing_time, 2)
                if self.last_crossing_time > 0
                else None
            ),
        }
