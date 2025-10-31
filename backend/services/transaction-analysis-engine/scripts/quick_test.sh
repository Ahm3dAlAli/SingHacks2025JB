#!/bin/bash
# Quick test run without formatting/linting

set -e

echo "Running quick tests..."

# Check if container is running
if ! docker ps | grep -q tae_service; then
    echo "TAE container not running. Please start with: docker-compose up -d"
    exit 1
fi

# Run tests
docker exec tae_service python -m pytest tests/ -v --tb=short

echo "Quick tests complete!"
