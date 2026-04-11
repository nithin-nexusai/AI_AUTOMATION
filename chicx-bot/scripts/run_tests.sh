#!/bin/bash

# CHICX Bot Test Runner Script
# Runs tests in Docker containers with PostgreSQL and Redis

set -e

echo "🧪 CHICX Bot Test Suite"
echo "======================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to project directory
cd "$(dirname "$0")/.."

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Docker is running"
}

# Function to start test services
start_services() {
    echo ""
    echo "🚀 Starting test services (PostgreSQL + Redis)..."
    docker-compose -f docker-compose.test.yml up -d postgres-test redis-test
    
    echo "⏳ Waiting for services to be healthy..."
    sleep 5
    
    # Check if services are healthy
    if docker-compose -f docker-compose.test.yml ps | grep -q "unhealthy"; then
        echo -e "${RED}❌ Services failed to start properly${NC}"
        docker-compose -f docker-compose.test.yml logs
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Test services are ready"
}

# Function to run migrations
run_migrations() {
    echo ""
    echo "📊 Running database migrations..."
    
    export DATABASE_URL="postgresql+asyncpg://chicx_test:chicx_test_pass@localhost:5433/chicx_bot_test"
    export REDIS_URL="redis://localhost:6380/0"
    
    # Activate venv if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    alembic upgrade head
    echo -e "${GREEN}✓${NC} Migrations completed"
}

# Function to run tests
run_tests() {
    echo ""
    echo "🧪 Running tests..."
    echo ""
    
    export DATABASE_URL="postgresql+asyncpg://chicx_test:chicx_test_pass@localhost:5433/chicx_bot_test"
    export REDIS_URL="redis://localhost:6380/0"
    export PYTHONPATH=$PWD
    
    # Activate venv if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Run tests based on argument
    case "${1:-all}" in
        unit)
            echo "Running unit tests only..."
            pytest tests/unit/ -v --cov=app --cov-report=html --cov-report=term
            ;;
        integration)
            echo "Running integration tests only..."
            pytest tests/integration/ -v --cov=app --cov-report=html --cov-report=term
            ;;
        e2e)
            echo "Running E2E tests only..."
            pytest tests/e2e/ -v --cov=app --cov-report=html --cov-report=term
            ;;
        all)
            echo "Running all tests..."
            pytest tests/ -v --cov=app --cov-report=html --cov-report=term
            ;;
        *)
            echo "Running tests: $1"
            pytest "$1" -v --cov=app --cov-report=html --cov-report=term
            ;;
    esac
}

# Function to stop services
stop_services() {
    echo ""
    echo "🛑 Stopping test services..."
    docker-compose -f docker-compose.test.yml down
    echo -e "${GREEN}✓${NC} Services stopped"
}

# Function to clean up
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    docker-compose -f docker-compose.test.yml down -v
    echo -e "${GREEN}✓${NC} Cleanup complete"
}

# Main execution
main() {
    check_docker
    
    # Handle commands
    case "${1:-run}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        clean)
            cleanup
            ;;
        run)
            start_services
            run_migrations
            run_tests "${2:-all}"
            TEST_EXIT_CODE=$?
            stop_services
            exit $TEST_EXIT_CODE
            ;;
        docker)
            # Run tests completely in Docker
            echo "🐳 Running tests in Docker container..."
            docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit test-runner
            docker-compose -f docker-compose.test.yml down
            ;;
        *)
            echo "Usage: $0 {start|stop|clean|run [unit|integration|e2e|all]|docker}"
            echo ""
            echo "Commands:"
            echo "  start       - Start test services (PostgreSQL + Redis)"
            echo "  stop        - Stop test services"
            echo "  clean       - Stop services and remove volumes"
            echo "  run [type]  - Start services, run tests, then stop (default)"
            echo "  docker      - Run tests completely in Docker"
            echo ""
            echo "Test types:"
            echo "  unit        - Run unit tests only"
            echo "  integration - Run integration tests only"
            echo "  e2e         - Run E2E tests only"
            echo "  all         - Run all tests (default)"
            echo ""
            echo "Examples:"
            echo "  $0 run unit              # Run unit tests"
            echo "  $0 run integration       # Run integration tests"
            echo "  $0 docker                # Run all tests in Docker"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

# Made with Bob
