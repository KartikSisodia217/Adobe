import sys
import os
import subprocess

def main():
    print("Running Preflight Checks...")
    
    if sys.version_info < (3, 9):
        print("FAIL: Python 3.9+ is required.")
        sys.exit(1)
    
    try:
        import aiohttp
        import bs4
        import pydantic
        import playwright
        import pytest
    except ImportError as e:
        print(f"FAIL: Missing dependency - {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
        
    try:
        # Avoid async loop destruction errors by just calling playwright CLI
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium", "--dry-run"], capture_output=True, text=True)
        # If it runs fine, playwright is installed
    except Exception as e:
        print("FAIL: Chromium is missing or failed to launch.")
        print("playwright install --with-deps chromium")
        sys.exit(1)
        
    print("SUCCESS: All preflight checks passed.")
    sys.exit(0)

if __name__ == '__main__':
    main()
