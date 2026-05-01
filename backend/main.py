import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from routes.simulation_routes import create_router
from services.simulation_service import simulation_service, simulation_service_2

app = FastAPI(title="Thread Intersection Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# index.html  →  /api  +  /ws
app.include_router(create_router(simulation_service), prefix="/api")

# index2.html  →  /api2  +  /ws2
app.include_router(create_router(simulation_service_2), prefix="/api2")


@app.websocket("/ws")
async def websocket_main(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            state = simulation_service.get_state()
            await websocket.send_text(json.dumps(state))
            await asyncio.sleep(0.05)
    except (WebSocketDisconnect, Exception):
        pass


@app.websocket("/ws2")
async def websocket_comparison(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            state = simulation_service_2.get_state()
            await websocket.send_text(json.dumps(state))
            await asyncio.sleep(0.05)
    except (WebSocketDisconnect, Exception):
        pass
