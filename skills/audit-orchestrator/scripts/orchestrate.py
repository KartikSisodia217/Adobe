#!/usr/bin/env python3
import os
import sys

# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.orchestration.cli import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
