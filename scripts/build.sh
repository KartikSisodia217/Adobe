#!/bin/bash
set -e

echo "Validating marketplace..."
PYTHONPATH="." python3 scripts/validate_marketplace.py

echo "Creating package..."
rm -f aimless-marketplace.zip

zip -rq aimless-marketplace.zip \
    marketplace.json \
    README.md \
    LICENSE \
    requirements.txt \
    requirements-test.txt \
    pytest.ini \
    skills/ \
    src/ \
    tests/ \
    scripts/validate_marketplace.py \
    -x "*__pycache__*" "*.pyc" "*.DS_Store" "*/.DS_Store" "*.pdf" "venv/*" ".git/*"

SIZE=$(wc -c < aimless-marketplace.zip | tr -d ' ')
echo "Package size: $SIZE bytes"

MAX_SIZE=52428800 # 50 MB
if [ "$SIZE" -gt "$MAX_SIZE" ]; then
    echo "ERROR: Package exceeds 50MB limit."
    exit 1
fi

echo "Build successful: aimless-marketplace.zip ($SIZE bytes)"
