#!/usr/bin/env python3
import logging
import os
import asyncio
from pathlib import Path

import src.common.config as config

async def setup_webserver() -> None:
    """Setup web server configuration."""
    # Import the new proxy API
    from src.proxy.api.main import app
    import uvicorn
    
    # Get configuration
    from src.proxy.config import settings
    
    print(f"Starting {settings.app.name} on {settings.app.host}:{settings.app.port}")
    
    # Run the server
    uvicorn.run(
        app,
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload,
        workers=settings.app.workers if not settings.app.reload else 1
    )

async def setup_transporter() -> None:
    """Setup transporter configuration."""
    # Keep existing transporter if needed
    pass

async def setup_gradio() -> None:
    """Setup gradio configuration."""
    # Keep existing gradio if needed
    pass
    
async def main() -> None:
    """Main application entry point."""
    try:
        print("Starting OpenAI Proxy application...")

        # For the proxy, we mainly need the web server
        await setup_webserver()
        
        print("OpenAI Proxy started successfully.")

    except Exception as e:
        logging.error(f"Application failed to start: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
