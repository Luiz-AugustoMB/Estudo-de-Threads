from dataclasses import dataclass
from enum import Enum


class CarState(str, Enum):
    MOVING = "moving"
    IN_CRITICAL = "in_critical"
    COLLIDED = "collided"
    FINISHED = "finished"


class Direction(str, Enum):
    NORTH = "north"   # entra pelo topo,     desce       (pista esquerda vertical)
    SOUTH = "south"   # entra pela base,     sobe        (pista direita vertical)
    WEST  = "west"    # entra pela esquerda, vai direita (pista superior horizontal)
    EAST  = "east"    # entra pela direita,  vai esquerda (pista inferior horizontal)


@dataclass
class Car:
    id: str
    direction: Direction
    x: float
    y: float
    state: CarState = CarState.MOVING
    time_in_critical: float = 0.0   # segundos acumulados na região crítica
    speed: float = 0.0              # velocidade individual da thread (px/passo)
    quadrant: str = ""              # sub-região atual: "Q1"–"Q4" ou ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "direction": self.direction.value,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "state": self.state.value,
            "time_in_critical": round(self.time_in_critical, 2),
            "speed": round(self.speed, 2),
            "quadrant": self.quadrant,
        }
