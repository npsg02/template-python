"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import v1_router


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

    return app


# Create default app instance
app = create_app()
