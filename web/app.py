"""
JARVIS FastAPI Dashboard Application.

Sets up the local FastAPI web server, mounts static frontend assets,
registers REST API routes and the WebSocket event stream endpoint.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.routes import router as api_router
from web.state import event_bus, web_state
from web.websocket import ws_manager

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages FastAPI application startup and graceful shutdown events.
    """
    logger.info("JARVIS Web Dashboard Server starting up...")
    event_bus.publish("system", data={"message": "JARVIS Web Dashboard Server online."})
    yield
    logger.info("JARVIS Web Dashboard Server shutting down...")
    event_bus.publish("system", data={"message": "JARVIS Web Dashboard Server offline."})


# Initialize FastAPI App
app = FastAPI(
    title="JARVIS Web Dashboard",
    version="0.1.0-alpha",
    description="Local web dashboard and REST/WebSocket API for the JARVIS AI Assistant.",
    lifespan=lifespan
)

# Enable CORS for local binding security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API Router
app.include_router(api_router)


# WebSocket Real-Time Event Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint broadcasting real-time system events to connected dashboard clients.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and receive optional ping messages
            data = await websocket.receive_text()
            logger.debug("Received message on WebSocket endpoint: %s", data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug("WebSocket connection closed with error: %s", e)
        await ws_manager.disconnect(websocket)


# Serve Static Frontend Assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_index() -> FileResponse:
    """
    Serves the primary HTML5 dashboard interface.
    """
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"Dashboard index.html missing at {index_path}")
    return FileResponse(index_path)


def create_app() -> FastAPI:
    """
    Factory function returning the configured FastAPI application instance.

    Returns:
        FastAPI: The web application instance.
    """
    return app
