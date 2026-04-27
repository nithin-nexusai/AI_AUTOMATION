#!/bin/bash

################################################################################
# CHICX Bot Deployment Script
# 
# This script automates the deployment of the CHICX bot to AWS EC2
# 
# Usage:
#   ./scripts/deploy.sh [environment]
#
# Environments:
#   - production (default)
#   - staging
#   - development
#
# Prerequisites:
#   - SSH access to EC2 instance
#   - Docker and Docker Compose installed on EC2
#   - .env file configured
#
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment-specific configuration
if [ -f "$PROJECT_ROOT/.env.$ENVIRONMENT" ]; then
    source "$PROJECT_ROOT/.env.$ENVIRONMENT"
else
    echo -e "${RED}Error: .env.$ENVIRONMENT file not found${NC}"
    exit 1
fi

# Required variables
: "${EC2_HOST:?EC2_HOST not set in .env.$ENVIRONMENT}"
: "${EC2_USER:=ubuntu}"
: "${EC2_KEY:?EC2_KEY not set in .env.$ENVIRONMENT}"
: "${DEPLOY_PATH:=/opt/chicx-bot}"

################################################################################
# Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if SSH key exists
    if [ ! -f "$EC2_KEY" ]; then
        log_error "SSH key not found: $EC2_KEY"
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found in project root"
        exit 1
    fi
    
    # Check SSH connection
    if ! ssh -i "$EC2_KEY" -o ConnectTimeout=5 "$EC2_USER@$EC2_HOST" "echo 'SSH connection successful'" > /dev/null 2>&1; then
        log_error "Cannot connect to EC2 instance: $EC2_HOST"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

backup_current_deployment() {
    log_info "Creating backup of current deployment..."
    
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" << 'EOF'
        if [ -d /opt/chicx-bot ]; then
            BACKUP_DIR="/opt/chicx-bot-backups"
            BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
            
            mkdir -p "$BACKUP_DIR"
            
            # Backup database
            cd /opt/chicx-bot
            if docker-compose ps | grep -q "db"; then
                docker-compose exec -T db pg_dump -U chicx chicx > "$BACKUP_DIR/$BACKUP_NAME-db.sql"
                echo "Database backed up to $BACKUP_DIR/$BACKUP_NAME-db.sql"
            fi
            
            # Backup .env file
            cp .env "$BACKUP_DIR/$BACKUP_NAME.env"
            
            # Keep only last 5 backups
            cd "$BACKUP_DIR"
            ls -t | tail -n +11 | xargs -r rm
            
            echo "Backup created: $BACKUP_NAME"
        fi
EOF
    
    log_success "Backup completed"
}

upload_files() {
    log_info "Uploading files to EC2..."
    
    # Create temporary directory for deployment
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT
    
    # Copy files to temp directory
    rsync -av --exclude='.git' \
              --exclude='__pycache__' \
              --exclude='*.pyc' \
              --exclude='.pytest_cache' \
              --exclude='node_modules' \
              --exclude='.env.local' \
              "$PROJECT_ROOT/" "$TEMP_DIR/"
    
    # Upload to EC2
    rsync -avz --delete \
          -e "ssh -i $EC2_KEY" \
          "$TEMP_DIR/" \
          "$EC2_USER@$EC2_HOST:$DEPLOY_PATH/"
    
    # Upload .env file separately
    scp -i "$EC2_KEY" "$PROJECT_ROOT/.env" "$EC2_USER@$EC2_HOST:$DEPLOY_PATH/.env"
    
    log_success "Files uploaded successfully"
}

install_dependencies() {
    log_info "Installing dependencies on EC2..."
    
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" << EOF
        cd $DEPLOY_PATH
        
        # Check if Docker is installed
        if ! command -v docker &> /dev/null; then
            echo "Installing Docker..."
            curl -fsSL https://get.docker.com | sudo sh
            sudo usermod -aG docker $EC2_USER
        fi
        
        # Check if Docker Compose is installed
        if ! command -v docker-compose &> /dev/null; then
            echo "Installing Docker Compose..."
            sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
        fi
        
        echo "Dependencies installed"
EOF
    
    log_success "Dependencies installed"
}

build_and_start() {
    log_info "Building and starting services..."
    
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" << EOF
        cd $DEPLOY_PATH
        
        # Pull latest images
        docker-compose pull
        
        # Build custom images
        docker-compose build
        
        # Start services
        docker-compose up -d
        
        # Wait for services to be healthy
        echo "Waiting for services to start..."
        sleep 10
        
        # Check service status
        docker-compose ps
EOF
    
    log_success "Services started"
}

run_migrations() {
    log_info "Running database migrations..."
    
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" << EOF
        cd $DEPLOY_PATH
        
        # Wait for database to be ready
        echo "Waiting for database..."
        for i in {1..30}; do
            if docker-compose exec -T db pg_isready -U chicx > /dev/null 2>&1; then
                echo "Database is ready"
                break
            fi
            echo "Waiting for database... \$i/30"
            sleep 2
        done
        
        # Run migrations
        docker-compose exec -T app alembic upgrade head
        
        # Verify migrations
        docker-compose exec -T app alembic current
EOF
    
    log_success "Migrations completed"
}

import_data() {
    log_info "Importing FAQ data..."
    
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" << EOF
        cd $DEPLOY_PATH
        
        # Import FAQs
        if [ -d "docs/faqs" ]; then
            docker-compose exec -T app python scripts/import_faqs.py
        fi
        
        # Generate embeddings
        docker-compose exec -T app python scripts/generate_embeddings.py
EOF
    
    log_success "Data imported"
}

health_check() {
    log_info "Running health checks..."
    
    # Wait for application to be ready
    sleep 5
    
    # Check health endpoint
    HEALTH_URL="http://$EC2_HOST:8000/health"
    
    for i in {1..30}; do
        if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
            log_success "Health check passed"
            return 0
        fi
        echo "Waiting for application... $i/30"
        sleep 2
    done
    
    log_error "Health check failed"
    return 1
}

show_logs() {
    log_info "Showing recent logs..."
    
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" << EOF
        cd $DEPLOY_PATH
        docker-compose logs --tail=50 app
EOF
}

print_summary() {
    log_success "Deployment completed successfully!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Deployment Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Environment:     $ENVIRONMENT"
    echo "  EC2 Host:        $EC2_HOST"
    echo "  Deploy Path:     $DEPLOY_PATH"
    echo ""
    echo "  Health Check:    http://$EC2_HOST:8000/health"
    echo "  WhatsApp:        http://$EC2_HOST:8000/webhooks/whatsapp"
    echo "  Bolna:           http://$EC2_HOST:8000/webhooks/bolna"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Next steps:"
    echo "  1. Setup CloudFront distribution"
    echo "  2. Update DNS records"
    echo "  3. Update WhatsApp webhook URL"
    echo "  4. Update Bolna tool URLs"
    echo "  5. Test all features"
    echo ""
    echo "Useful commands:"
    echo "  View logs:       ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'cd $DEPLOY_PATH && docker-compose logs -f app'"
    echo "  Restart:         ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'cd $DEPLOY_PATH && docker-compose restart app'"
    echo "  Status:          ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'cd $DEPLOY_PATH && docker-compose ps'"
    echo ""
}

rollback() {
    log_warning "Rolling back to previous deployment..."
    
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" << 'EOF'
        BACKUP_DIR="/opt/chicx-bot-backups"
        LATEST_BACKUP=$(ls -t "$BACKUP_DIR" | grep "backup-" | head -1 | cut -d'-' -f2-3)
        
        if [ -z "$LATEST_BACKUP" ]; then
            echo "No backup found to rollback to"
            exit 1
        fi
        
        echo "Rolling back to backup: $LATEST_BACKUP"
        
        cd /opt/chicx-bot
        
        # Stop services
        docker-compose down
        
        # Restore .env
        cp "$BACKUP_DIR/backup-$LATEST_BACKUP.env" .env
        
        # Restore database
        if [ -f "$BACKUP_DIR/backup-$LATEST_BACKUP-db.sql" ]; then
            docker-compose up -d db
            sleep 5
            docker-compose exec -T db psql -U chicx chicx < "$BACKUP_DIR/backup-$LATEST_BACKUP-db.sql"
        fi
        
        # Start services
        docker-compose up -d
        
        echo "Rollback completed"
EOF
    
    log_success "Rollback completed"
}

################################################################################
# Main
################################################################################

main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  CHICX Bot Deployment"
    echo "  Environment: $ENVIRONMENT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Backup current deployment
    backup_current_deployment
    
    # Upload files
    upload_files
    
    # Install dependencies
    install_dependencies
    
    # Build and start services
    build_and_start
    
    # Run migrations
    run_migrations
    
    # Import data
    import_data
    
    # Health check
    if ! health_check; then
        log_error "Deployment failed health check"
        read -p "Do you want to rollback? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback
        fi
        exit 1
    fi
    
    # Show logs
    show_logs
    
    # Print summary
    print_summary
}

# Handle script arguments
case "${1:-}" in
    --rollback)
        rollback
        exit 0
        ;;
    --help|-h)
        echo "Usage: $0 [environment] [options]"
        echo ""
        echo "Environments:"
        echo "  production (default)"
        echo "  staging"
        echo "  development"
        echo ""
        echo "Options:"
        echo "  --rollback    Rollback to previous deployment"
        echo "  --help        Show this help message"
        exit 0
        ;;
    *)
        main
        ;;
esac

# Made with Bob
