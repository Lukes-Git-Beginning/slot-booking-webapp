#!/bin/bash
# SSL Error Monitoring Script
# Tracks SSL errors in business-hub error logs

LOG_FILE="/var/log/business-hub/error.log"
OUTPUT_FILE="/var/log/business-hub/ssl_error_summary.log"
ALERT_THRESHOLD=5  # Alert if more than 5 SSL errors per hour

# Get current timestamp
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
ONE_HOUR_AGO=$(date -d '1 hour ago' '+%Y-%m-%d %H:%M')

# Count SSL errors in the last hour
SSL_ERROR_COUNT=$(grep "SSL" "$LOG_FILE" | grep "$ONE_HOUR_AGO" | wc -l)

# Log summary
echo "[$TIMESTAMP] SSL Errors in last hour: $SSL_ERROR_COUNT" >> "$OUTPUT_FILE"

# Alert if threshold exceeded
if [ "$SSL_ERROR_COUNT" -gt "$ALERT_THRESHOLD" ]; then
    echo "[$TIMESTAMP] ⚠️  ALERT: $SSL_ERROR_COUNT SSL errors detected (threshold: $ALERT_THRESHOLD)" >> "$OUTPUT_FILE"

    # Extract last 5 SSL errors for details
    echo "Last 5 SSL errors:" >> "$OUTPUT_FILE"
    grep "SSL" "$LOG_FILE" | tail -5 >> "$OUTPUT_FILE"
    echo "---" >> "$OUTPUT_FILE"
fi

# Cleanup old summary logs (keep last 7 days)
find /var/log/business-hub/ -name "ssl_error_summary.log" -mtime +7 -delete

# Check worker memory and log if high
MEMORY_USAGE=$(ps aux | grep gunicorn | grep -v grep | awk '{sum+=$6} END {print sum/1024}')
echo "[$TIMESTAMP] Gunicorn total memory usage: ${MEMORY_USAGE}MB" >> "$OUTPUT_FILE"

# Alert if memory exceeds 500MB
if (( $(echo "$MEMORY_USAGE > 500" | bc -l) )); then
    echo "[$TIMESTAMP] ⚠️  ALERT: High memory usage detected: ${MEMORY_USAGE}MB" >> "$OUTPUT_FILE"
fi
