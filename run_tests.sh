#!/bin/bash

# Test runner script for AI Meal Planner

set -e

echo "=================================="
echo "AI Meal Planner Test Suite"
echo "=================================="
echo ""

# Check if pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo "❌ pytest not found. Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Default to running all tests with coverage
if [ "$1" == "fast" ]; then
    echo "🚀 Running tests (fast mode - no coverage)..."
    pytest -v
elif [ "$1" == "watch" ]; then
    echo "👀 Running tests in watch mode..."
    pytest-watch -v
elif [ "$1" == "unit" ]; then
    echo "🧪 Running unit tests only..."
    pytest tests/test_utils.py tests/test_ai.py -v
elif [ "$1" == "integration" ]; then
    echo "🔗 Running integration tests..."
    pytest tests/test_routes.py -v
elif [ "$1" == "coverage" ]; then
    echo "📊 Running tests with detailed coverage..."
    pytest --cov=app --cov-report=html --cov-report=term-missing --cov-branch
    echo ""
    echo "✅ Coverage report generated in htmlcov/index.html"
else
    echo "🧪 Running all tests with coverage..."
    pytest
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "Usage:"
    echo "  ./run_tests.sh          - Run all tests with coverage (default)"
    echo "  ./run_tests.sh fast     - Run tests without coverage"
    echo "  ./run_tests.sh coverage - Run tests with detailed coverage report"
    echo "  ./run_tests.sh unit     - Run only unit tests"
    echo "  ./run_tests.sh integration - Run only integration tests"
fi
