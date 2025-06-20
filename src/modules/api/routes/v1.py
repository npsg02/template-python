"""API v1 route handlers."""

from fastapi import APIRouter
from typing import Dict, List
from src.modules.transporter import publish_message

# Create v1 router
router = APIRouter(prefix='/v1', tags=['v1'])

@router.get("/hello")
async def hello_world() -> Dict[str, str]:
    """Hello world endpoint."""
    publish_message("hello-python", "Hello from FastAPI!")
    return {"message": "Hello, World!"}

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

@router.get("/metrics")
async def metrics() -> Dict[str, int]:
    """Application metrics endpoint."""
    return {
        "total_routes": len(router.routes),
        "api_version": 1
    }
