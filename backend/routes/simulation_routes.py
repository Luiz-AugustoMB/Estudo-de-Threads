from fastapi import APIRouter
from pydantic import BaseModel
from services.simulation_service import simulation_service

router = APIRouter()


class StartBody(BaseModel):
    num_cars:  int   = 4
    max_delay: float = 3.5   # dispersão máxima de partida em segundos (0–6)


class SpeedBody(BaseModel):
    level: int = 4   # 1 (lento) – 12 (rápido)


@router.post("/start")
def start(body: StartBody):
    n     = max(1,   min(body.num_cars,  20))
    delay = max(0.0, min(body.max_delay,  6.0))
    simulation_service.start(n, max_delay=delay)
    return {"status": "ok", "num_cars": n}


@router.post("/speed")
def set_speed(body: SpeedBody):
    level = max(1, min(body.level, 12))
    simulation_service.set_speed(level)
    return {"status": "ok", "step_delay": simulation_service._step_delay}


@router.post("/reset")
def reset():
    simulation_service.reset()
    return {"status": "ok"}


@router.get("/state")
def get_state():
    return simulation_service.get_state()
