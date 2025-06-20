#!/usr/bin/env python3
import logging
import os
from pathlib import Path
from typing import Dict
import asyncio

async def setup_webserver() -> None:
    """Setup web server configuration."""
    # Placeholder for web server setup logic
    from src.modules.api import server
    await server()

async def setup_transporter() -> None:
    """Setup transporter configuration."""
    # Placeholder for transporter setup logic
    # import src.modules.
    import src.modules.transporter
    
async def main() -> None:
    """Main application entry point."""
    try:
        print("Start app...")
        # import src.modules.transporter
        task1 = asyncio.create_task(setup_webserver())
        task2 = asyncio.create_task(setup_transporter())
        await asyncio.gather(task1, task2)
        print("App started successfully.")
      
        

    except Exception as e:
        logging.error(f"Application failed to start: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
