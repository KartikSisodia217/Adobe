#!/bin/bash
set -e

echo "Validating marketplace..."
./scripts/validate_marketplace.py

echo "Creating package..."
rm -f aimless-marketplace.zip
zip -rq aimless-marketplace.zip . -x "*.git*" "*__pycache__*" "*.pyc" "venv/*" "tests/*" ".DS_Store" "scripts/build.sh" "*.pdf"

SIZE=$(stat -f %z aimless-marketplace.zip 2>/dev/null || stat -c %s aimless-marketplace.zip)
echo "Package size: $SIZE bytes"

MAX_SIZE=52428800 # 50 MB
if [ $SIZE -gt $MAX_SIZE ]; then
    echo "ERROR: Package exceeds 50MB limit."
    exit 1
fi

echo "Build successful."
