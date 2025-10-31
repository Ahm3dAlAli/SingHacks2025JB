#!/bin/bash
# Run tests inside Docker container

set -e

echo "================================"
echo "Running TASK-004 Tests"
echo "================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if container is running
if ! docker ps | grep -q tae_service; then
    echo -e "${YELLOW}TAE container not running. Starting services...${NC}"
    docker-compose up -d
    echo "Waiting for services to be healthy..."
    sleep 10
fi

echo ""
echo "================================"
echo "Step 1: Format Code with Black"
echo "================================"
docker exec tae_service python -m black app/ tests/ --line-length=100 || {
    echo -e "${YELLOW}Black not installed or failed, skipping formatting${NC}"
}

echo ""
echo "================================"
echo "Step 2: Run Linting with Ruff"
echo "================================"
docker exec tae_service python -m ruff check app/ tests/ --fix || {
    echo -e "${YELLOW}Ruff not installed or failed, skipping linting${NC}"
}

echo ""
echo "================================"
echo "Step 3: Run Unit Tests"
echo "================================"
docker exec tae_service python -m pytest tests/test_agents/ -v --tb=short || {
    echo -e "${RED}Unit tests failed!${NC}"
    exit 1
}

echo ""
echo "================================"
echo "Step 4: Run Integration Tests"
echo "================================"
docker exec tae_service python -m pytest tests/test_integration/ -v --tb=short || {
    echo -e "${RED}Integration tests failed!${NC}"
    exit 1
}

echo ""
echo "================================"
echo "Step 5: Run All Tests with Coverage"
echo "================================"
docker exec tae_service python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html || {
    echo -e "${RED}Coverage tests failed!${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}All Tests Passed! ✓${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Coverage report generated in htmlcov/"
echo "View with: open htmlcov/index.html"
