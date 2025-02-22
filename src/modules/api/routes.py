"""API route definitions."""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class RouteConfig:
    """Configuration for an API route."""
    path: str
    methods: List[str]
    description: str
    version: Optional[str] = "v1"

# Example route configurations
ROUTES = [
    RouteConfig(
        path="/api/v1/health",
        methods=["GET"],
        description="Health check endpoint",
    ),
    RouteConfig(
        path="/api/v1/metrics",
        methods=["GET"],
        description="Application metrics endpoint",
    ),
]

def get_route_config(path: str) -> Optional[RouteConfig]:
    """Get route configuration by path.
    
    Args:
        path: The API route path
        
    Returns:
        Optional[RouteConfig]: The route configuration if found, None otherwise
    """
    return next((route for route in ROUTES if route.path == path), None)

def list_routes() -> List[RouteConfig]:
    """List all available API routes.
    
    Returns:
        List[RouteConfig]: List of all route configurations
    """
    return ROUTES