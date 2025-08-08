"""Main FastAPI application for the OpenAI proxy."""

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .v1 import router as v1_router
from .admin import router as admin_router
from .middleware import (
    RequestIDMiddleware, LoggingMiddleware, AuthenticationMiddleware,
    RateLimitMiddleware, AuditMiddleware
)
from ..config import settings


# Prometheus metrics
REQUEST_COUNT = Counter('proxy_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('proxy_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
PROVIDER_REQUESTS = Counter('proxy_provider_requests_total', 'Provider requests', ['provider', 'model', 'status'])
FALLBACK_COUNT = Counter('proxy_fallbacks_total', 'Fallback attempts', ['model', 'reason'])


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.app.name,
        description=settings.app.description,
        version=settings.app.version,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=settings.app.cors_allow_credentials,
        allow_methods=settings.app.cors_allow_methods,
        allow_headers=settings.app.cors_allow_headers,
    )
    
    # Add custom middleware in reverse order (last added = first executed)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    # Include routers
    app.include_router(v1_router)
    app.include_router(admin_router)
    
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        """Middleware to collect Prometheus metrics."""
        start_time = time.time()
        
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": settings.app.version
        }
    
    @app.get("/readyz")
    async def readiness_check():
        """Readiness check endpoint."""
        # In a real implementation, check database connectivity, Redis, etc.
        return {
            "status": "ready",
            "timestamp": time.time()
        }
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Log the error
        import logging
        logger = logging.getLogger("openai_proxy")
        logger.error(f"Unhandled exception in request {request_id}: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error",
                    "request_id": request_id
                }
            },
            headers={"X-Proxy-Request-ID": request_id}
        )
    
    @app.on_event("startup")
    async def startup_event():
        """Run startup tasks."""
        print(f"Starting {settings.app.name} v{settings.app.version}")
        print(f"Environment: {settings.app.debug}")
        print(f"Database: {settings.database.url}")
        print(f"Redis: {settings.redis.url}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Run shutdown tasks."""
        print("Shutting down OpenAI proxy...")
    
    return app


# Create app instance
app = create_app()