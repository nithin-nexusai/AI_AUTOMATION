#!/bin/bash

################################################################################
# CHICX Bot Monitoring Setup Script
# 
# This script sets up comprehensive monitoring for the CHICX bot
# 
# Features:
#   - System resource monitoring
#   - Application health checks
#   - Log monitoring and alerts
#   - Automated notifications
#   - Performance metrics
#
# Usage:
#   ./scripts/setup-monitoring.sh
#
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

################################################################################
# Install Monitoring Tools
################################################################################

install_tools() {
    log_info "Installing monitoring tools..."
    
    sudo apt update
    sudo apt install -y \
        htop \
        iotop \
        nethogs \
        sysstat \
        jq \
        curl \
        mailutils
    
    log_success "Monitoring tools installed"
}

################################################################################
# Setup Health Check Script
################################################################################

setup_health_check() {
    log_info "Setting up health check script..."
    
    cat > /opt/chicx-bot/scripts/health-check.sh << 'EOF'
#!/bin/bash

# Health check script for CHICX bot

HEALTH_URL="http://localhost:8000/health"
LOG_FILE="/var/log/chicx-bot/health-check.log"
ALERT_EMAIL="${ALERT_EMAIL:-admin@thechicx.com}"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Function to send alert
send_alert() {
    local subject="$1"
    local message="$2"
    
    echo "$message" | mail -s "$subject" "$ALERT_EMAIL"
    echo "[$(date)] ALERT: $subject - $message" >> "$LOG_FILE"
}

# Check health endpoint
check_health() {
    local response=$(curl -sf "$HEALTH_URL" 2>&1)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "[$(date)] Health check passed" >> "$LOG_FILE"
        return 0
    else
        echo "[$(date)] Health check failed: $response" >> "$LOG_FILE"
        send_alert "CHICX Bot Health Check Failed" "Health endpoint returned error: $response"
        return 1
    fi
}

# Check Docker containers
check_containers() {
    cd /opt/chicx-bot
    
    local containers=$(docker-compose ps -q)
    local running=$(docker-compose ps | grep -c "Up" || true)
    local total=$(docker-compose ps -a | grep -c "chicx-bot" || true)
    
    if [ "$running" -lt "$total" ]; then
        send_alert "CHICX Bot Container Down" "Some containers are not running. Running: $running/$total"
        return 1
    fi
    
    echo "[$(date)] All containers running ($running/$total)" >> "$LOG_FILE"
    return 0
}

# Check disk space
check_disk_space() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -gt 80 ]; then
        send_alert "CHICX Bot Disk Space Warning" "Disk usage is at ${usage}%"
        return 1
    fi
    
    echo "[$(date)] Disk usage: ${usage}%" >> "$LOG_FILE"
    return 0
}

# Check memory usage
check_memory() {
    local usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    
    if [ "$usage" -gt 90 ]; then
        send_alert "CHICX Bot Memory Warning" "Memory usage is at ${usage}%"
        return 1
    fi
    
    echo "[$(date)] Memory usage: ${usage}%" >> "$LOG_FILE"
    return 0
}

# Check database connection
check_database() {
    cd /opt/chicx-bot
    
    if docker-compose exec -T db pg_isready -U chicx > /dev/null 2>&1; then
        echo "[$(date)] Database connection OK" >> "$LOG_FILE"
        return 0
    else
        send_alert "CHICX Bot Database Connection Failed" "Cannot connect to PostgreSQL database"
        return 1
    fi
}

# Check Redis connection
check_redis() {
    cd /opt/chicx-bot
    
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "[$(date)] Redis connection OK" >> "$LOG_FILE"
        return 0
    else
        send_alert "CHICX Bot Redis Connection Failed" "Cannot connect to Redis"
        return 1
    fi
}

# Main health check
main() {
    echo "[$(date)] Starting health check..." >> "$LOG_FILE"
    
    local failed=0
    
    check_health || ((failed++))
    check_containers || ((failed++))
    check_disk_space || ((failed++))
    check_memory || ((failed++))
    check_database || ((failed++))
    check_redis || ((failed++))
    
    if [ $failed -eq 0 ]; then
        echo "[$(date)] All health checks passed" >> "$LOG_FILE"
        exit 0
    else
        echo "[$(date)] $failed health check(s) failed" >> "$LOG_FILE"
        exit 1
    fi
}

main
EOF
    
    chmod +x /opt/chicx-bot/scripts/health-check.sh
    
    log_success "Health check script created"
}

################################################################################
# Setup Log Monitoring
################################################################################

setup_log_monitoring() {
    log_info "Setting up log monitoring..."
    
    cat > /opt/chicx-bot/scripts/monitor-logs.sh << 'EOF'
#!/bin/bash

# Log monitoring script for CHICX bot

LOG_FILE="/var/log/chicx-bot/monitor.log"
ALERT_EMAIL="${ALERT_EMAIL:-admin@thechicx.com}"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Function to send alert
send_alert() {
    local subject="$1"
    local message="$2"
    
    echo "$message" | mail -s "$subject" "$ALERT_EMAIL"
    echo "[$(date)] ALERT: $subject" >> "$LOG_FILE"
}

# Check for errors in application logs
check_errors() {
    cd /opt/chicx-bot
    
    local errors=$(docker-compose logs --tail=100 app 2>&1 | grep -i "error" | wc -l)
    
    if [ "$errors" -gt 10 ]; then
        local error_sample=$(docker-compose logs --tail=100 app 2>&1 | grep -i "error" | tail -5)
        send_alert "CHICX Bot High Error Rate" "Found $errors errors in last 100 log lines. Sample:\n\n$error_sample"
    fi
    
    echo "[$(date)] Found $errors errors in logs" >> "$LOG_FILE"
}

# Check for critical errors
check_critical() {
    cd /opt/chicx-bot
    
    local critical=$(docker-compose logs --tail=100 app 2>&1 | grep -i "critical\|fatal" | wc -l)
    
    if [ "$critical" -gt 0 ]; then
        local critical_sample=$(docker-compose logs --tail=100 app 2>&1 | grep -i "critical\|fatal")
        send_alert "CHICX Bot Critical Error" "Found critical errors:\n\n$critical_sample"
    fi
    
    echo "[$(date)] Found $critical critical errors" >> "$LOG_FILE"
}

# Check for database errors
check_db_errors() {
    cd /opt/chicx-bot
    
    local db_errors=$(docker-compose logs --tail=100 db 2>&1 | grep -i "error\|fatal" | wc -l)
    
    if [ "$db_errors" -gt 5 ]; then
        local error_sample=$(docker-compose logs --tail=100 db 2>&1 | grep -i "error\|fatal" | tail -5)
        send_alert "CHICX Bot Database Errors" "Found $db_errors database errors. Sample:\n\n$error_sample"
    fi
    
    echo "[$(date)] Found $db_errors database errors" >> "$LOG_FILE"
}

# Main monitoring
main() {
    echo "[$(date)] Starting log monitoring..." >> "$LOG_FILE"
    
    check_errors
    check_critical
    check_db_errors
    
    echo "[$(date)] Log monitoring completed" >> "$LOG_FILE"
}

main
EOF
    
    chmod +x /opt/chicx-bot/scripts/monitor-logs.sh
    
    log_success "Log monitoring script created"
}

################################################################################
# Setup Performance Monitoring
################################################################################

setup_performance_monitoring() {
    log_info "Setting up performance monitoring..."
    
    cat > /opt/chicx-bot/scripts/monitor-performance.sh << 'EOF'
#!/bin/bash

# Performance monitoring script for CHICX bot

METRICS_FILE="/var/log/chicx-bot/metrics.log"

# Create log directory
mkdir -p "$(dirname "$METRICS_FILE")"

# Collect system metrics
collect_system_metrics() {
    local timestamp=$(date +%s)
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    local mem_usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    echo "$timestamp,system,cpu,$cpu_usage" >> "$METRICS_FILE"
    echo "$timestamp,system,memory,$mem_usage" >> "$METRICS_FILE"
    echo "$timestamp,system,disk,$disk_usage" >> "$METRICS_FILE"
}

# Collect Docker metrics
collect_docker_metrics() {
    cd /opt/chicx-bot
    
    local timestamp=$(date +%s)
    
    # Get container stats
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | tail -n +2 | while read line; do
        local container=$(echo "$line" | awk '{print $1}')
        local cpu=$(echo "$line" | awk '{print $2}' | sed 's/%//')
        local mem=$(echo "$line" | awk '{print $3}' | sed 's/MiB//')
        
        echo "$timestamp,docker,$container-cpu,$cpu" >> "$METRICS_FILE"
        echo "$timestamp,docker,$container-mem,$mem" >> "$METRICS_FILE"
    done
}

# Collect application metrics
collect_app_metrics() {
    local timestamp=$(date +%s)
    
    # Get response time
    local response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
    echo "$timestamp,app,response_time,$response_time" >> "$METRICS_FILE"
    
    # Get request count (from logs)
    cd /opt/chicx-bot
    local requests=$(docker-compose logs --tail=100 app 2>&1 | grep -c "POST\|GET" || echo 0)
    echo "$timestamp,app,requests,$requests" >> "$METRICS_FILE"
}

# Main monitoring
main() {
    collect_system_metrics
    collect_docker_metrics
    collect_app_metrics
    
    # Keep only last 7 days of metrics
    find "$(dirname "$METRICS_FILE")" -name "metrics.log" -mtime +7 -delete
}

main
EOF
    
    chmod +x /opt/chicx-bot/scripts/monitor-performance.sh
    
    log_success "Performance monitoring script created"
}

################################################################################
# Setup Automated Restart
################################################################################

setup_auto_restart() {
    log_info "Setting up automated restart..."
    
    cat > /opt/chicx-bot/scripts/auto-restart.sh << 'EOF'
#!/bin/bash

# Automated restart script for CHICX bot

LOG_FILE="/var/log/chicx-bot/auto-restart.log"
MAX_RESTARTS=3
RESTART_COUNT_FILE="/tmp/chicx-bot-restart-count"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Initialize restart count
if [ ! -f "$RESTART_COUNT_FILE" ]; then
    echo "0" > "$RESTART_COUNT_FILE"
fi

# Check if bot is healthy
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    # Bot is healthy, reset restart count
    echo "0" > "$RESTART_COUNT_FILE"
    exit 0
fi

# Bot is unhealthy, check restart count
RESTART_COUNT=$(cat "$RESTART_COUNT_FILE")

if [ "$RESTART_COUNT" -ge "$MAX_RESTARTS" ]; then
    echo "[$(date)] Max restarts ($MAX_RESTARTS) reached. Manual intervention required." >> "$LOG_FILE"
    echo "CHICX Bot requires manual intervention after $MAX_RESTARTS failed restart attempts" | \
        mail -s "CHICX Bot Critical - Manual Intervention Required" "${ALERT_EMAIL:-admin@thechicx.com}"
    exit 1
fi

# Restart bot
echo "[$(date)] Bot unhealthy. Attempting restart ($((RESTART_COUNT + 1))/$MAX_RESTARTS)..." >> "$LOG_FILE"

cd /opt/chicx-bot
docker-compose restart app

# Increment restart count
echo "$((RESTART_COUNT + 1))" > "$RESTART_COUNT_FILE"

# Wait and check if restart was successful
sleep 30

if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[$(date)] Restart successful" >> "$LOG_FILE"
    echo "0" > "$RESTART_COUNT_FILE"
else
    echo "[$(date)] Restart failed" >> "$LOG_FILE"
fi
EOF
    
    chmod +x /opt/chicx-bot/scripts/auto-restart.sh
    
    log_success "Auto-restart script created"
}

################################################################################
# Setup Cron Jobs
################################################################################

setup_cron_jobs() {
    log_info "Setting up cron jobs..."
    
    # Create cron file
    cat > /tmp/chicx-bot-cron << 'EOF'
# CHICX Bot Monitoring Cron Jobs

# Health check every 5 minutes
*/5 * * * * /opt/chicx-bot/scripts/health-check.sh >> /var/log/chicx-bot/cron.log 2>&1

# Log monitoring every 10 minutes
*/10 * * * * /opt/chicx-bot/scripts/monitor-logs.sh >> /var/log/chicx-bot/cron.log 2>&1

# Performance monitoring every 5 minutes
*/5 * * * * /opt/chicx-bot/scripts/monitor-performance.sh >> /var/log/chicx-bot/cron.log 2>&1

# Auto-restart check every 5 minutes
*/5 * * * * /opt/chicx-bot/scripts/auto-restart.sh >> /var/log/chicx-bot/cron.log 2>&1

# Daily backup at 2 AM
0 2 * * * /opt/chicx-bot/scripts/backup.sh >> /var/log/chicx-bot/cron.log 2>&1

# Weekly cleanup at 3 AM on Sunday
0 3 * * 0 /opt/chicx-bot/scripts/cleanup.sh >> /var/log/chicx-bot/cron.log 2>&1

# Daily metrics report at 9 AM
0 9 * * * /opt/chicx-bot/scripts/daily-report.sh >> /var/log/chicx-bot/cron.log 2>&1
EOF
    
    # Install cron jobs
    crontab -l > /tmp/current-cron 2>/dev/null || true
    cat /tmp/current-cron /tmp/chicx-bot-cron | crontab -
    rm /tmp/chicx-bot-cron /tmp/current-cron
    
    log_success "Cron jobs installed"
}

################################################################################
# Setup Log Rotation
################################################################################

setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    sudo tee /etc/logrotate.d/chicx-bot > /dev/null << 'EOF'
/var/log/chicx-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
    postrotate
        # Reload application if needed
    endscript
}

/opt/chicx-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
EOF
    
    log_success "Log rotation configured"
}

################################################################################
# Setup Backup Script
################################################################################

setup_backup_script() {
    log_info "Setting up backup script..."
    
    cat > /opt/chicx-bot/scripts/backup.sh << 'EOF'
#!/bin/bash

# Backup script for CHICX bot

BACKUP_DIR="/opt/chicx-bot-backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="/var/log/chicx-bot/backup.log"

# Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] Starting backup..." >> "$LOG_FILE"

cd /opt/chicx-bot

# Backup database
if docker-compose ps | grep -q "db"; then
    echo "[$(date)] Backing up database..." >> "$LOG_FILE"
    docker-compose exec -T db pg_dump -U chicx chicx | gzip > "$BACKUP_DIR/db-$TIMESTAMP.sql.gz"
fi

# Backup .env file
cp .env "$BACKUP_DIR/env-$TIMESTAMP"

# Backup uploaded files (if any)
if [ -d "uploads" ]; then
    tar -czf "$BACKUP_DIR/uploads-$TIMESTAMP.tar.gz" uploads/
fi

# Keep only last 7 days of backups
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "[$(date)] Backup completed: $TIMESTAMP" >> "$LOG_FILE"

# Upload to S3 (optional)
# aws s3 cp "$BACKUP_DIR/db-$TIMESTAMP.sql.gz" s3://chicx-bot-backups/
EOF
    
    chmod +x /opt/chicx-bot/scripts/backup.sh
    
    log_success "Backup script created"
}

################################################################################
# Setup Cleanup Script
################################################################################

setup_cleanup_script() {
    log_info "Setting up cleanup script..."
    
    cat > /opt/chicx-bot/scripts/cleanup.sh << 'EOF'
#!/bin/bash

# Cleanup script for CHICX bot

LOG_FILE="/var/log/chicx-bot/cleanup.log"

echo "[$(date)] Starting cleanup..." >> "$LOG_FILE"

cd /opt/chicx-bot

# Clean Docker images
echo "[$(date)] Cleaning Docker images..." >> "$LOG_FILE"
docker image prune -af --filter "until=168h"

# Clean Docker volumes
echo "[$(date)] Cleaning Docker volumes..." >> "$LOG_FILE"
docker volume prune -f

# Clean old logs
echo "[$(date)] Cleaning old logs..." >> "$LOG_FILE"
find /var/log/chicx-bot -name "*.log" -mtime +30 -delete

# Clean old backups
echo "[$(date)] Cleaning old backups..." >> "$LOG_FILE"
find /opt/chicx-bot-backups -type f -mtime +30 -delete

# Clean temporary files
echo "[$(date)] Cleaning temporary files..." >> "$LOG_FILE"
find /tmp -name "chicx-bot-*" -mtime +7 -delete

echo "[$(date)] Cleanup completed" >> "$LOG_FILE"
EOF
    
    chmod +x /opt/chicx-bot/scripts/cleanup.sh
    
    log_success "Cleanup script created"
}

################################################################################
# Setup Daily Report
################################################################################

setup_daily_report() {
    log_info "Setting up daily report..."
    
    cat > /opt/chicx-bot/scripts/daily-report.sh << 'EOF'
#!/bin/bash

# Daily report script for CHICX bot

REPORT_FILE="/tmp/chicx-bot-daily-report.txt"
ALERT_EMAIL="${ALERT_EMAIL:-admin@thechicx.com}"

# Generate report
cat > "$REPORT_FILE" << 'REPORT'
CHICX Bot Daily Report
======================
Date: $(date)

System Status:
--------------
CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
Memory Usage: $(free -h | grep Mem | awk '{print $3 "/" $2}')
Disk Usage: $(df -h / | awk 'NR==2 {print $5}')

Docker Containers:
------------------
$(cd /opt/chicx-bot && docker-compose ps)

Recent Errors (last 24 hours):
-------------------------------
$(cd /opt/chicx-bot && docker-compose logs --since 24h app 2>&1 | grep -i "error" | tail -10)

Health Checks:
--------------
$(tail -20 /var/log/chicx-bot/health-check.log)

Performance Metrics (last 24 hours):
------------------------------------
Average Response Time: $(awk -F',' '/app,response_time/ {sum+=$4; count++} END {if(count>0) print sum/count "s"; else print "N/A"}' /var/log/chicx-bot/metrics.log)
Total Requests: $(awk -F',' '/app,requests/ {sum+=$4} END {print sum}' /var/log/chicx-bot/metrics.log)

Backup Status:
--------------
$(tail -5 /var/log/chicx-bot/backup.log)

REPORT

# Send report
mail -s "CHICX Bot Daily Report - $(date +%Y-%m-%d)" "$ALERT_EMAIL" < "$REPORT_FILE"

# Clean up
rm "$REPORT_FILE"
EOF
    
    chmod +x /opt/chicx-bot/scripts/daily-report.sh
    
    log_success "Daily report script created"
}

################################################################################
# Setup Dashboard
################################################################################

setup_dashboard() {
    log_info "Setting up monitoring dashboard..."
    
    cat > /opt/chicx-bot/scripts/dashboard.sh << 'EOF'
#!/bin/bash

# Monitoring dashboard for CHICX bot

clear

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              CHICX Bot Monitoring Dashboard                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# System Info
echo "┌─ System Status ────────────────────────────────────────────────┐"
echo "│ CPU Usage:    $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')"
echo "│ Memory:       $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "│ Disk:         $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')"
echo "│ Uptime:       $(uptime -p)"
echo "└────────────────────────────────────────────────────────────────┘"
echo ""

# Docker Status
echo "┌─ Docker Containers ────────────────────────────────────────────┐"
cd /opt/chicx-bot
docker-compose ps | tail -n +2 | while read line; do
    echo "│ $line"
done
echo "└────────────────────────────────────────────────────────────────┘"
echo ""

# Health Status
echo "┌─ Health Checks ────────────────────────────────────────────────┐"
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "│ ✓ Application:  Healthy"
else
    echo "│ ✗ Application:  Unhealthy"
fi

if docker-compose exec -T db pg_isready -U chicx > /dev/null 2>&1; then
    echo "│ ✓ Database:     Connected"
else
    echo "│ ✗ Database:     Disconnected"
fi

if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "│ ✓ Redis:        Connected"
else
    echo "│ ✗ Redis:        Disconnected"
fi
echo "└────────────────────────────────────────────────────────────────┘"
echo ""

# Recent Logs
echo "┌─ Recent Logs (last 10 lines) ─────────────────────────────────┐"
docker-compose logs --tail=10 app 2>&1 | sed 's/^/│ /'
echo "└────────────────────────────────────────────────────────────────┘"
echo ""

echo "Press Ctrl+C to exit, or run with 'watch' for live updates:"
echo "  watch -n 5 /opt/chicx-bot/scripts/dashboard.sh"
EOF
    
    chmod +x /opt/chicx-bot/scripts/dashboard.sh
    
    log_success "Dashboard script created"
}

################################################################################
# Main
################################################################################

main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║         CHICX Bot Monitoring Setup                             ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    install_tools
    setup_health_check
    setup_log_monitoring
    setup_performance_monitoring
    setup_auto_restart
    setup_backup_script
    setup_cleanup_script
    setup_daily_report
    setup_dashboard
    setup_log_rotation
    setup_cron_jobs
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║         Monitoring Setup Complete!                             ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Monitoring features installed:"
    echo "  ✓ Health checks (every 5 minutes)"
    echo "  ✓ Log monitoring (every 10 minutes)"
    echo "  ✓ Performance monitoring (every 5 minutes)"
    echo "  ✓ Auto-restart (on failure)"
    echo "  ✓ Daily backups (2 AM)"
    echo "  ✓ Weekly cleanup (Sunday 3 AM)"
    echo "  ✓ Daily reports (9 AM)"
    echo ""
    echo "Useful commands:"
    echo "  View dashboard:     /opt/chicx-bot/scripts/dashboard.sh"
    echo "  Live dashboard:     watch -n 5 /opt/chicx-bot/scripts/dashboard.sh"
    echo "  Manual health check: /opt/chicx-bot/scripts/health-check.sh"
    echo "  Manual backup:      /opt/chicx-bot/scripts/backup.sh"
    echo "  View logs:          tail -f /var/log/chicx-bot/*.log"
    echo ""
    echo "Configure email alerts:"
    echo "  export ALERT_EMAIL=your-email@example.com"
    echo "  Add to /etc/environment for persistence"
    echo ""
}

main

# Made with Bob
