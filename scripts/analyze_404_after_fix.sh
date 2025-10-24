#!/bin/bash
# 404 Analysis Script - Check if decorator fix reduced 404 errors
# Run at 16:00 to analyze period after fix deployment (12:46)

NGINX_LOG="/var/log/nginx/business-hub-access.log"
OUTPUT_FILE="/var/log/business-hub/404_analysis_$(date +%Y%m%d_%H%M).txt"
FIX_TIME="24/Oct/2025:12:46"  # When decorator fix was deployed

echo "========================================" > "$OUTPUT_FILE"
echo "404 Error Analysis - Post-Fix Report" >> "$OUTPUT_FILE"
echo "========================================" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "Fix deployed at: 12:46 UTC" >> "$OUTPUT_FILE"
echo "Analysis time: $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$OUTPUT_FILE"
echo "Time window: 12:46 - 16:00 (3h 14min)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Total 404 count since fix
echo "## 1. Total 404 Errors Since Fix" >> "$OUTPUT_FILE"
echo "-----------------------------------" >> "$OUTPUT_FILE"
TOTAL_404=$(grep " 404 " "$NGINX_LOG" | awk -v ft="[$FIX_TIME" '$4 > ft' | wc -l)
echo "Total 404 errors: $TOTAL_404" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Most common 404 URLs
echo "## 2. Most Common 404 URLs" >> "$OUTPUT_FILE"
echo "-----------------------------------" >> "$OUTPUT_FILE"
grep " 404 " "$NGINX_LOG" | awk -v ft="[$FIX_TIME" '$4 > ft' | cut -d'"' -f2 | cut -d' ' -f2 | sort | uniq -c | sort -rn | head -10 >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# API endpoint status codes (should be 401 not 404)
echo "## 3. API Endpoint Status Codes (/api/*)" >> "$OUTPUT_FILE"
echo "-----------------------------------" >> "$OUTPUT_FILE"
echo "Expected: 401 (Unauthorized) instead of 404" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
grep "/api/" "$NGINX_LOG" | awk -v ft="[$FIX_TIME" '$4 > ft' | grep -E " 401 | 404 " | awk '{print $7, $9}' | sort | uniq -c | sort -rn >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Specifically check our fixed endpoints
echo "## 4. Fixed Endpoints - Status Distribution" >> "$OUTPUT_FILE"
echo "-----------------------------------" >> "$OUTPUT_FILE"
echo "### /api/user/badges:" >> "$OUTPUT_FILE"
grep "/api/user/badges" "$NGINX_LOG" | awk -v ft="[$FIX_TIME" '$4 > ft' | awk '{print $9}' | sort | uniq -c | sort -rn >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "### /api/level/check-up:" >> "$OUTPUT_FILE"
grep "/api/level/check-up" "$NGINX_LOG" | awk -v ft="[$FIX_TIME" '$4 > ft' | awk '{print $9}' | sort | uniq -c | sort -rn >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Compare before/after (last 3 hours before fix vs 3 hours after)
echo "## 5. Before/After Comparison (3h windows)" >> "$OUTPUT_FILE"
echo "-----------------------------------" >> "$OUTPUT_FILE"
BEFORE_START="24/Oct/2025:09:46"
BEFORE_END="24/Oct/2025:12:45"
AFTER_START="24/Oct/2025:12:46"
AFTER_END="24/Oct/2025:15:59"

BEFORE_404=$(grep " 404 " "$NGINX_LOG" | awk -v start="[$BEFORE_START" -v end="[$BEFORE_END" '$4 > start && $4 < end' | wc -l)
AFTER_404=$(grep " 404 " "$NGINX_LOG" | awk -v start="[$AFTER_START" -v end="[$AFTER_END" '$4 > start && $4 < end' | wc -l)

echo "BEFORE fix (09:46-12:45): $BEFORE_404 errors" >> "$OUTPUT_FILE"
echo "AFTER fix  (12:46-15:59): $AFTER_404 errors" >> "$OUTPUT_FILE"

if [ "$BEFORE_404" -gt 0 ]; then
    REDUCTION=$(echo "scale=1; ($BEFORE_404 - $AFTER_404) * 100 / $BEFORE_404" | bc)
    echo "Reduction: ${REDUCTION}%" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# SSL error check from monitoring
echo "## 6. SSL Errors (from monitoring)" >> "$OUTPUT_FILE"
echo "-----------------------------------" >> "$OUTPUT_FILE"
if [ -f "/var/log/business-hub/ssl_error_summary.log" ]; then
    tail -5 /var/log/business-hub/ssl_error_summary.log >> "$OUTPUT_FILE"
else
    echo "No SSL monitoring data available" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# Summary
echo "========================================" >> "$OUTPUT_FILE"
echo "SUMMARY" >> "$OUTPUT_FILE"
echo "========================================" >> "$OUTPUT_FILE"
if [ "$AFTER_404" -lt "$BEFORE_404" ]; then
    echo "✅ SUCCESS: 404 errors reduced!" >> "$OUTPUT_FILE"
elif [ "$AFTER_404" -eq "$BEFORE_404" ]; then
    echo "⚠️  NEUTRAL: No change in 404 count" >> "$OUTPUT_FILE"
else
    echo "❌ ISSUE: 404 errors increased, needs investigation" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# Print to stdout as well
cat "$OUTPUT_FILE"

echo ""
echo "Full report saved to: $OUTPUT_FILE"
