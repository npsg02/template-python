"""Common configuration utilities."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class AppConfig:
    """Application configuration."""

    app_name: str
    environment: str
    debug: bool
    log_level: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables.

        Returns:
            AppConfig: Application configuration instance
        """
        return cls(
            app_name=os.getenv("APP_NAME", "template-python"),
            environment=os.getenv("ENV", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def load_json_config(path: Path) -> dict[str, Any]:
    """Load configuration from JSON file.

    Args:
        path: Path to JSON configuration file

    Returns:
        dict[str, Any]: Configuration dictionary

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        json.JSONDecodeError: If configuration file is invalid JSON
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open() as f:
        return json.load(f)


class ConfigurationError(Exception):
    """Base class for configuration errors."""

    pass


def get_config_path(config_name: str) -> Path:
    """Get configuration file path.

    Args:
        config_name: Name of the configuration file

    Returns:
        Path: Path to configuration file
    """
    # Check common configuration locations
    locations = [
        Path("config"),  # Project config directory
        Path("~/.config/template-python"),  # User config directory
        Path("/etc/template-python"),  # System config directory
    ]

    for location in locations:
        path = location.expanduser() / f"{config_name}.json"
        if path.exists():
            return path

    return locations[0].expanduser() / f"{config_name}.json"
