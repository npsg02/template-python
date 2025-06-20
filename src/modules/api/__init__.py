import uvicorn
from .app import app as api_app
import logging

async def server():
    """Main application entry point."""
    try:
        print("Start api...")
        config = uvicorn.Config(api_app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    except Exception as e:
        logging.error(f"Application failed to start: {e}", exc_info=True)
        raise
