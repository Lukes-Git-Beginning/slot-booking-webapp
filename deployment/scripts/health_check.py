#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internal Health Check Script for Business Hub
Monitors all critical services and sends alerts if issues detected
"""

import sys
import os
import subprocess
import json
import requests
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)

# Health check configuration
CHECKS = {
    "gunicorn": "systemctl is-active business-hub",
    "nginx": "systemctl is-active nginx",
    "fail2ban": "systemctl is-active fail2ban",
}

LOG_FILE = "/var/log/business-hub/health-check.log"
ALERT_FILE = "/tmp/business-hub-last-alert.txt"
ALERT_COOLDOWN = 3600  # 1 hour between alerts

def log(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)

    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_msg + "\n")
    except Exception as e:
        print(f"Failed to write log: {e}")

def check_service(name, command):
    """Check if a service is running"""
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=5
        )
        is_active = result.returncode == 0 and result.stdout.strip() == "active"
        return is_active, result.stdout.strip() if not is_active else "active"
    except Exception as e:
        return False, str(e)

def check_http_endpoint():
    """Check if Flask app responds"""
    try:
        # Use env var or default to localhost
        health_url = os.getenv("HEALTH_CHECK_URL", "http://127.0.0.1:5000/health")
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, str(e)

def check_disk_space():
    """Check available disk space"""
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            usage = parts[4].replace("%", "")
            return int(usage) < 90, f"{usage}%"
        return False, "Unable to parse"
    except Exception as e:
        return False, str(e)

def check_memory():
    """Check available memory"""
    try:
        result = subprocess.run(
            ["free", "-m"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            total = int(parts[1])
            available = int(parts[6])
            usage_percent = int((1 - available/total) * 100)
            return usage_percent < 90, f"{usage_percent}%"
        return False, "Unable to parse"
    except Exception as e:
        return False, str(e)

def check_persistent_data():
    """Check if persistent data directory is accessible"""
    try:
        data_dir = Path("/opt/business-hub/data/persistent")
        if not data_dir.exists():
            return False, "Directory does not exist"

        # Try to list files
        files = list(data_dir.glob("*.json"))
        return True, f"{len(files)} JSON files found"
    except Exception as e:
        return False, str(e)

def should_send_alert():
    """Check if we should send alert (cooldown check)"""
    try:
        if not os.path.exists(ALERT_FILE):
            return True

        with open(ALERT_FILE, "r") as f:
            last_alert = float(f.read().strip())

        return (datetime.now().timestamp() - last_alert) > ALERT_COOLDOWN
    except:
        return True

def mark_alert_sent():
    """Mark that an alert was sent"""
    try:
        with open(ALERT_FILE, "w") as f:
            f.write(str(datetime.now().timestamp()))
    except Exception as e:
        log(f"Failed to mark alert sent: {e}")

def send_alert(issues):
    """Log critical issues (email integration can be added here)"""
    log("="*60)
    log("⚠️  CRITICAL: Health check failed!")
    log("="*60)
    for issue in issues:
        log(f"  ❌ {issue}")
    log("="*60)

    # TODO: Add email notification here if needed
    # Example: send_email(subject="Business Hub Alert", body="\n".join(issues))

def main():
    """Run all health checks"""
    log("Starting health check...")

    issues = []
    all_ok = True

    # Check systemd services
    for service_name, command in CHECKS.items():
        is_ok, details = check_service(service_name, command)
        if is_ok:
            log(f"✓ {service_name}: {details}")
        else:
            log(f"✗ {service_name}: {details}")
            issues.append(f"{service_name} is not active: {details}")
            all_ok = False

    # Check HTTP endpoint
    is_ok, details = check_http_endpoint()
    if is_ok:
        log(f"✓ Flask App: HTTP {details}")
    else:
        log(f"✗ Flask App: {details}")
        issues.append(f"Flask app not responding: {details}")
        all_ok = False

    # Check disk space
    is_ok, details = check_disk_space()
    if is_ok:
        log(f"✓ Disk Space: {details} used")
    else:
        log(f"✗ Disk Space: {details}")
        issues.append(f"Disk space critical: {details}")
        all_ok = False

    # Check memory
    is_ok, details = check_memory()
    if is_ok:
        log(f"✓ Memory: {details} used")
    else:
        log(f"✗ Memory: {details}")
        issues.append(f"Memory usage critical: {details}")
        all_ok = False

    # Check persistent data
    is_ok, details = check_persistent_data()
    if is_ok:
        log(f"✓ Persistent Data: {details}")
    else:
        log(f"✗ Persistent Data: {details}")
        issues.append(f"Persistent data issue: {details}")
        all_ok = False

    # Send alert if there are issues
    if not all_ok:
        if should_send_alert():
            send_alert(issues)
            mark_alert_sent()
        else:
            log("Alert suppressed (cooldown period)")
        return 1

    log("✓ All checks passed!")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"FATAL ERROR: Health check script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
