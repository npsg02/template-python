"""Module loader utilities."""

import logging
import uvicorn
from typing import Any, Optional

from src.modules.api.app import app as api_app
from src.modules.api.core.config import settings

logger = logging.getLogger(__name__)

class ModuleLoader:
    """Utility class for loading and running modules."""
    
    @staticmethod
    def load_api(
        host: str = "0.0.0.0",
        port: int = 8000,
        reload: bool = False,
        **kwargs: Any
    ) -> None:
        """Load and run the API module.
        
        Args:
            host: Host to bind the server to
            port: Port to bind the server to
            reload: Enable auto-reload for development
            **kwargs: Additional uvicorn configuration
        """
        logger.info(f"Starting API server on {host}:{port}")
        logger.debug(f"API Settings: {settings.dict()}")
        
        config = uvicorn.Config(
            api_app,
            host=host,
            port=port,
            reload=reload,
            log_level="debug" if settings.debug else "info",
            **kwargs
        )
        
        server = uvicorn.Server(config)
        server.run()

    @classmethod
    def load_module(
        cls,
        module_name: str,
        **kwargs: Any
    ) -> Optional[Any]:
        """Generic module loader.
        
        Args:
            module_name: Name of the module to load
            **kwargs: Module-specific configuration
            
        Returns:
            Optional[Any]: Module instance if applicable
        """
        if module_name == "api":
            cls.load_api(**kwargs)
            return api_app
        else:
            logger.error(f"Unknown module: {module_name}")
            return None