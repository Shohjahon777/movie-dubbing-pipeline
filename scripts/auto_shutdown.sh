#!/bin/bash
# Auto-shutdown Script
# Monitors activity and shuts down droplet if idle
# Add to cron: @hourly /root/dubbing-mvp/scripts/auto_shutdown.sh

PROJECT_DIR="/root/dubbing-mvp"
IDLE_THRESHOLD_MINUTES=60
LOG_FILE="$PROJECT_DIR/logs/auto_shutdown.log"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Checking for activity..."

# Check if pipeline is running
if pgrep -f "node src/index.js" > /dev/null; then
    log "Pipeline active, not shutting down"
    exit 0
fi

# Check if API is processing requests
if pgrep -f "python.*app.py" > /dev/null; then
    # Check last activity in temp directory
    TEMP_DIR="$PROJECT_DIR/data/temp"
    if [ -d "$TEMP_DIR" ]; then
        LAST_ACTIVITY=$(find "$TEMP_DIR" -type f -mmin -$IDLE_THRESHOLD_MINUTES 2>/dev/null | wc -l)
        
        if [ "$LAST_ACTIVITY" -gt 0 ]; then
            log "Recent activity detected ($LAST_ACTIVITY files), not shutting down"
            exit 0
        fi
    fi
fi

# Check last activity in output directory
OUTPUT_DIR="$PROJECT_DIR/data/output"
if [ -d "$OUTPUT_DIR" ]; then
    LAST_OUTPUT=$(find "$OUTPUT_DIR" -type f -mmin -$IDLE_THRESHOLD_MINUTES 2>/dev/null | wc -l)
    
    if [ "$LAST_OUTPUT" -gt 0 ]; then
        log "Recent output detected ($LAST_OUTPUT files), not shutting down"
        exit 0
    fi
fi

# No activity detected
log "No activity in last $IDLE_THRESHOLD_MINUTES minutes"
log "Shutting down droplet..."

# Uncomment the line below to enable auto-shutdown
# shutdown -h now

log "Auto-shutdown disabled (uncomment shutdown command to enable)"

