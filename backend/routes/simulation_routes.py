from fastapi import APIRouter, Body
from pydantic import BaseModel

from services.simulation_service import simulation_service

router = APIRouter()


class StartRequest(BaseModel):
    sync_enabled: bool = True
    scheduling_mode: str = "fcfs"


@router.post("/start")
def start(payload: StartRequest | None = Body(default=None)):
    sync_enabled = payload.sync_enabled if payload is not None else True
    scheduling_mode = payload.scheduling_mode if payload is not None else "fcfs"
    simulation_service.start(sync_enabled=sync_enabled, scheduling_mode=scheduling_mode)
    return {"status": "ok", "sync_enabled": sync_enabled, "scheduling_mode": scheduling_mode}


@router.post("/reset")
def reset():
    simulation_service.reset()
    return {"status": "ok"}


@router.get("/state")
def get_state():
    return simulation_service.get_state()
