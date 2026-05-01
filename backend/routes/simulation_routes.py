from fastapi import APIRouter, Body
from pydantic import BaseModel

from services.simulation_service import SimulationService


class StartRequest(BaseModel):
    sync_enabled: bool = True
    scheduling_mode: str = "fcfs"


def create_router(service: SimulationService) -> APIRouter:
    router = APIRouter()

    @router.post("/start")
    def start(payload: StartRequest | None = Body(default=None)):
        sync_enabled = payload.sync_enabled if payload is not None else True
        scheduling_mode = payload.scheduling_mode if payload is not None else "fcfs"
        service.start(sync_enabled=sync_enabled, scheduling_mode=scheduling_mode)
        return {"status": "ok", "sync_enabled": sync_enabled, "scheduling_mode": scheduling_mode}

    @router.post("/reset")
    def reset():
        service.reset()
        return {"status": "ok"}

    @router.get("/state")
    def get_state():
        return service.get_state()

    return router
