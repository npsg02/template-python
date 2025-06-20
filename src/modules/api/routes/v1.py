"""API v1 route handlers."""

from fastapi import APIRouter, Response
from typing import Dict, List
from src.modules.transporter import publish_message
from src.modules.models.index import embed_text
import io
# Create v1 router
router = APIRouter(prefix='/v1', tags=['v1'])
import matplotlib.pyplot as plt

@router.get("/hello")
async def hello_world():
    """Hello world endpoint."""
    publish_message("hello-python", "Hello from FastAPI!")
    embed = embed_text("Hello, world!")
    print(f"Generated embedding: {embed}")
    return {"message": "Hello, reloaded!", "embedding": list(embed)}

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

@router.get("/plot")
async def get_plot():
    # Tạo biểu đồ
    plt.figure(figsize=(6, 4))
    x = [1, 2, 3, 4, 5]
    y = [i ** 2 for i in x]
    plt.plot(x, y, label="y = x^2")
    plt.title("Sample Plot")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.legend()

    # Lưu vào buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)

    # Trả về dưới dạng ảnh PNG
    return Response(content=buf.getvalue(), media_type="image/png")