import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from routes.simulation_routes import router
from services.simulation_service import simulation_service

app = FastAPI(title="Thread Intersection Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            state = simulation_service.get_state()
            await websocket.send_text(json.dumps(state))
            await asyncio.sleep(0.05)   # 20 fps
    except (WebSocketDisconnect, Exception):
        pass
