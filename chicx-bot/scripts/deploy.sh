#!/bin/bash
set -e

echo "🚀 Starting deployment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_PATH="/opt/chicx-bot"
BACKUP_PATH="/data/backups"
COMPOSE_FILE="docker-compose.prod.yml"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Change to deployment directory
cd $DEPLOY_PATH

# Check if .env exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    exit 1
fi

print_status "Environment file found"

# Pull latest images
print_status "Pulling latest Docker images..."
docker-compose -f $COMPOSE_FILE pull

# Build application
print_status "Building application..."
docker-compose -f $COMPOSE_FILE build --no-cache app

# Run database migrations
print_status "Running database migrations..."
docker-compose -f $COMPOSE_FILE run --rm app alembic upgrade head

# Restart services with zero downtime
print_status "Restarting services..."

# Start new containers
docker-compose -f $COMPOSE_FILE up -d

# Wait for health check
print_status "Waiting for services to be healthy..."
sleep 10

# Check if app is healthy
if docker-compose -f $COMPOSE_FILE exec -T app curl -f http://localhost:8000/admin/health > /dev/null 2>&1; then
    print_status "Health check passed!"
else
    print_error "Health check failed!"
    print_warning "Rolling back..."
    
    # Rollback
    if [ -d "$DEPLOY_PATH.backup.latest" ]; then
        cp -r $DEPLOY_PATH.backup.latest/* $DEPLOY_PATH/
        docker-compose -f $COMPOSE_FILE up -d
    fi
    
    exit 1
fi

# Clean up old images
print_status "Cleaning up old Docker images..."
docker image prune -f

# Clean up old backups (keep last 5)
print_status "Cleaning up old backups..."
ls -t $BACKUP_PATH/chicx_app_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm

print_status "Deployment completed successfully! 🎉"

# Show running containers
echo ""
echo "Running containers:"
docker-compose -f $COMPOSE_FILE ps

# Made with Bob
