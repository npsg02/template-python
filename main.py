#!/usr/bin/env python3
import logging
import os
from pathlib import Path
from typing import Dict
import asyncio

import src.common.config as config

async def setup_webserver() -> None:
    """Setup web server configuration."""
    from src.modules.api import server
    # import src.modules.yolo_train
    await server()
    pass

async def setup_transporter() -> None:
    """Setup transporter configuration."""
    import src.modules.transporter
    pass

async def setup_gradio() -> None:
    """Setup transporter configuration."""
    # import src.modules.gradio_app
    pass
    
async def main() -> None:
    """Main application entry point."""
    try:
        print("Start app...")

        # import src.modules.transporter
        task1 = asyncio.create_task(setup_webserver())
        task2 = asyncio.create_task(setup_transporter())
        task3 = asyncio.create_task(setup_gradio())
        await asyncio.gather(task1, task2, task3)
        print("App started successfully.")
      
        

    except Exception as e:
        logging.error(f"Application failed to start: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
