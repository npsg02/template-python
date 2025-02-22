#!/usr/bin/env python3

import logging
import os
from pathlib import Path
from typing import Dict


def main() -> None:
    """Main application entry point."""
    try:
        print("Start app...")
        import src.modules.api

    except Exception as e:
        print(f"Application failed to start: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
