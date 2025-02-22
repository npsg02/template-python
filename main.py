#!/usr/bin/env python3

import logging
import os
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_environment() -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    env_path = Path(".env")
    
    if env_path.exists():
        with env_path.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


def main() -> None:
    """Main application entry point."""
    try:
        # Load environment variables
        env_vars = setup_environment()
        app_name = env_vars.get("APP_NAME", "template-python")
        env = env_vars.get("ENV", "development")
        debug = env_vars.get("DEBUG", "false").lower() == "true"

        # Configure logging level based on debug setting
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")

        logger.info(f"Starting {app_name} in {env} environment")

        # Your application initialization code here
        # For example:
        # app = create_app()
        # app.run()

    except Exception as e:
        logger.error(f"Application failed to start: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()