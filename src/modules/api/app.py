"""FastAPI application factory."""

from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request

from .routes import v1_router

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
templates = Jinja2Templates(directory="templates")

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI()

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Include routers
    app.include_router(v1_router)

    @app.on_event("startup")
    async def startup_event():
        """Run startup events."""
        pass

    @app.on_event("shutdown")
    async def shutdown_event():
        """Run shutdown events."""
        pass
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                print(f"Received: {data}")
                await manager.broadcast(f"Message from client: {data}")
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            await manager.broadcast("A client disconnected")


    @app.get("/room/{room_name}", response_class=HTMLResponse)
    async def broadcaster(request: Request, room_name: str):
        return templates.TemplateResponse("broadcaster.html", {"request": request, "room_name": room_name})

    return app


# Create default app instance
app = create_app()
