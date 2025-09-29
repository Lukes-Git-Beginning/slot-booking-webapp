#!/bin/bash
# ==================================================
# Slot-Booking Application Deployment Script
# Phase 2: Application Installation und Konfiguration
# Ausführung nach server_setup.sh
# ==================================================

set -e  # Exit on any error

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging-Funktion
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# ==================================================
# KONFIGURATION
# ==================================================

APP_DIR="/opt/slot-booking"
APP_USER="$USER"
GIT_REPO="https://github.com/Lukes-Git-Beginning/slot-booking-webapp.git"  # Anpassen!
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="slot-booking"

# ==================================================
# VORAUSSETZUNGEN PRÜFEN
# ==================================================

check_prerequisites() {
    log "Checking prerequisites..."

    # App-Verzeichnis existiert?
    if [ ! -d "$APP_DIR" ]; then
        error "App directory $APP_DIR does not exist. Run server_setup.sh first!"
    fi

    # Virtual environment existiert?
    if [ ! -d "$VENV_DIR" ]; then
        error "Python virtual environment not found. Run server_setup.sh first!"
    fi

    # Nginx läuft?
    if ! systemctl is-active --quiet nginx; then
        error "Nginx is not running. Run server_setup.sh first!"
    fi

    # Git verfügbar?
    if ! command -v git &> /dev/null; then
        sudo apt update
        sudo apt install -y git
    fi

    log "Prerequisites check passed ✓"
}

# ==================================================
# UMGEBUNGSVARIABLEN KONFIGURIEREN
# ==================================================

configure_environment() {
    log "Configuring environment variables..."

    echo ""
    info "Please provide the following configuration values:"

    # Google Calendar Credentials
    echo ""
    warning "Google Calendar API Setup required:"
    echo "1. Go to: https://console.cloud.google.com/"
    echo "2. Create service account and download JSON credentials"
    echo "3. Convert to base64: cat service_account.json | base64 -w 0"
    echo ""

    read -p "Enter GOOGLE_CREDS_BASE64 (or press Enter to set later): " GOOGLE_CREDS
    read -p "Enter CENTRAL_CALENDAR_ID [zentralkalenderzfa@gmail.com]: " CALENDAR_ID
    CALENDAR_ID=${CALENDAR_ID:-zentralkalenderzfa@gmail.com}

    # Benutzer-Liste
    echo ""
    read -p "Enter USERLIST (format: user1:pass1,user2:pass2): " USERLIST

    # Admin-Benutzer
    echo ""
    read -p "Enter ADMIN_USERS (comma separated) [admin,Jose,Simon,Alex,David]: " ADMIN_USERS
    ADMIN_USERS=${ADMIN_USERS:-admin,Jose,Simon,Alex,David}

    # Secret Key generieren
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

    # T2-Closer-Konfiguration
    echo ""
    info "T2-Closer Configuration:"
    read -p "Enter T2_CLOSERS (format: Alexander:alex@domain.de,Daniel:daniel@domain.de): " T2_CLOSERS

    # .env-Datei erstellen
    tee $APP_DIR/.env > /dev/null <<EOF
# Slot-Booking Application Configuration
# Generated: $(date)

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY
DEBUG=False

# Google Calendar API
GOOGLE_CREDS_BASE64=$GOOGLE_CREDS
CENTRAL_CALENDAR_ID=$CALENDAR_ID

# User Management
USERLIST=$USERLIST
ADMIN_USERS=$ADMIN_USERS

# T2-Closer System
T2_CLOSERS=$T2_CLOSERS

# Data Persistence
PERSIST_BASE=$APP_DIR/data/persistent

# Logging
LOG_LEVEL=INFO
LOG_DIR=$APP_DIR/logs

# Performance
CACHE_TIMEOUT=300
MAX_EXPORT_RECORDS=10000

# Gamification
EXCLUDED_CHAMPION_USERS=admin,test

# Consultants (Standard)
CONSULTANTS=Sara:sara@zfa.com,Patrick:patrick@zfa.com,Dominik:dominik@zfa.com,Tim:tim@zfa.com,Ann-Kathrin:ann-kathrin@zfa.com

# Server Configuration
HOST=0.0.0.0
PORT=5000
EOF

    # Berechtigungen setzen
    chmod 600 $APP_DIR/.env
    chown $APP_USER:$APP_USER $APP_DIR/.env

    log "Environment configuration created ✓"
}

# ==================================================
# APPLICATION CODE DEPLOYMENT
# ==================================================

deploy_application() {
    log "Deploying application code..."

    cd $APP_DIR

    # Backup von bestehender Installation (falls vorhanden)
    if [ -d "app" ]; then
        warning "Existing installation found. Creating backup..."
        mv app app_backup_$(date +%Y%m%d_%H%M%S)
    fi

    # Repository klonen
    info "Cloning repository from $GIT_REPO"

    # Temporärer Clone
    git clone $GIT_REPO temp_clone

    # Dateien ins App-Verzeichnis kopieren
    cp -r temp_clone/* .
    cp -r temp_clone/.* . 2>/dev/null || true  # Hidden files

    # Temporären Clone löschen
    rm -rf temp_clone

    # Berechtigungen setzen
    chown -R $APP_USER:$APP_USER $APP_DIR
    find $APP_DIR -type f -name "*.py" -exec chmod 644 {} \;
    find $APP_DIR -type f -name "*.sh" -exec chmod 755 {} \;

    log "Application code deployed ✓"
}

# ==================================================
# PYTHON DEPENDENCIES
# ==================================================

install_dependencies() {
    log "Installing Python dependencies..."

    cd $APP_DIR

    # Virtual environment aktivieren
    source $VENV_DIR/bin/activate

    # Requirements installieren
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        error "requirements.txt not found in application directory"
    fi

    # Zusätzliche Production-Pakete
    pip install gunicorn

    # Dependencies-Liste speichern
    pip freeze > $APP_DIR/installed_packages.txt

    log "Python dependencies installed ✓"
}

# ==================================================
# DATENBANK/DATEN MIGRATION
# ==================================================

migrate_data() {
    log "Setting up data migration..."

    # Datenverzeichnisse erstellen
    mkdir -p $APP_DIR/data/persistent
    mkdir -p $APP_DIR/data/backups
    mkdir -p $APP_DIR/data/historical
    mkdir -p $APP_DIR/data/reports
    mkdir -p $APP_DIR/data/tracking

    # Legacy-Daten migrieren (falls vorhanden)
    if [ -d "$HOME/slot_booking_webapp/data" ]; then
        warning "Legacy data found. Migrating..."
        cp -r $HOME/slot_booking_webapp/data/* $APP_DIR/data/ 2>/dev/null || true
    fi

    # Berechtigungen setzen
    chown -R $APP_USER:$APP_USER $APP_DIR/data
    chmod -R 755 $APP_DIR/data

    # Datenintegrität prüfen
    cd $APP_DIR
    source $VENV_DIR/bin/activate

    # Data-Integrity-Check (falls verfügbar)
    if [ -f "check_data_integrity.py" ]; then
        python3 check_data_integrity.py
    fi

    log "Data migration completed ✓"
}

# ==================================================
# SYSTEMD SERVICE KONFIGURATION
# ==================================================

configure_service() {
    log "Configuring systemd service..."

    # Service-Datei aktualisieren
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Slot-Booking Flask Application
After=network.target

[Service]
Type=exec
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$VENV_DIR/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn --bind 127.0.0.1:5000 --workers 3 --timeout 120 run:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$APP_DIR/data $APP_DIR/logs
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF

    # Service laden und aktivieren
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME

    log "Systemd service configured ✓"
}

# ==================================================
# NGINX REVERSE PROXY
# ==================================================

configure_nginx() {
    log "Configuring Nginx reverse proxy..."

    # Nginx-Konfiguration für Slot-Booking
    sudo tee /etc/nginx/sites-available/slot-booking > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Static files
    location /static/ {
        alias /opt/slot-booking/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Favicon
    location /favicon.ico {
        alias /opt/slot-booking/static/favicon.ico;
        expires 1y;
    }

    # Main application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_buffering on;
        proxy_buffer_size 8k;
        proxy_buffers 16 8k;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        access_log off;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
    }

    location ~ /(\.env|requirements\.txt|README\.md)$ {
        deny all;
    }
}
EOF

    # Site aktivieren
    sudo ln -sf /etc/nginx/sites-available/slot-booking /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default

    # Nginx-Konfiguration testen
    sudo nginx -t

    # Nginx neu laden
    sudo systemctl reload nginx

    log "Nginx reverse proxy configured ✓"
}

# ==================================================
# T2-SYSTEM VORBEREITUNG
# ==================================================

setup_t2_system() {
    log "Setting up T2-Closer system..."

    cd $APP_DIR
    source $VENV_DIR/bin/activate

    # T2-Konfigurationsdatei erstellen
    tee $APP_DIR/t2_config.json > /dev/null <<EOF
{
    "t2_enabled": true,
    "closers": {
        "Alexander": "alexander@domain.de",
        "Daniel": "daniel@domain.de",
        "Christian": "christian@domain.de",
        "Tim": "tim@domain.de",
        "David": "david@domain.de",
        "Jose": "jose@domain.de"
    },
    "booking_duration_minutes": 120,
    "booking_hours": ["09:00", "11:00", "14:00", "16:00", "18:00"],
    "working_days": [1, 2, 3, 4, 5],
    "max_advance_days": 14
}
EOF

    # T2-Datenbankstrukturen erstellen
    mkdir -p $APP_DIR/data/persistent/t2
    touch $APP_DIR/data/persistent/t2/closer_bookings.json
    touch $APP_DIR/data/persistent/t2/closer_availability.json
    touch $APP_DIR/data/persistent/t2/closer_stats.json

    # Initialisierung (falls Script vorhanden)
    if [ -f "init_t2_system.py" ]; then
        python3 init_t2_system.py
    fi

    log "T2-Closer system prepared ✓"
}

# ==================================================
# LOGGING KONFIGURATION
# ==================================================

setup_logging() {
    log "Setting up application logging..."

    # Log-Verzeichnisse erstellen
    mkdir -p $APP_DIR/logs

    # Logrotate-Konfiguration
    sudo tee /etc/logrotate.d/slot-booking > /dev/null <<EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        systemctl reload slot-booking
    endscript
}
EOF

    # Logging-Konfiguration für Flask
    tee $APP_DIR/logging_config.py > /dev/null <<'EOF'
import logging
import logging.handlers
import os

def setup_logging(app):
    """Configure logging for production"""

    log_dir = app.config.get('LOG_DIR', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Main application log
    app_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app_handler.setLevel(logging.INFO)
    app.logger.addHandler(app_handler)

    # Calendar operations log
    calendar_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'calendar.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    calendar_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))

    calendar_logger = logging.getLogger('calendar')
    calendar_logger.addHandler(calendar_handler)
    calendar_logger.setLevel(logging.INFO)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Slot-Booking application started')
EOF

    log "Logging configuration completed ✓"
}

# ==================================================
# HEALTH CHECK ENDPOINT
# ==================================================

create_health_check() {
    log "Creating health check endpoint..."

    # Health-Check-Script
    tee $APP_DIR/health_check.py > /dev/null <<'EOF'
#!/usr/bin/env python3
"""
Health check endpoint for Slot-Booking application
"""

import json
import sys
import os
from datetime import datetime

def check_health():
    """Perform health checks"""

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # Database/Files check
    try:
        data_dir = "/opt/slot-booking/data/persistent"
        if os.path.exists(data_dir) and os.listdir(data_dir):
            health_status["checks"]["database"] = "ok"
        else:
            health_status["checks"]["database"] = "error"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Disk space check
    try:
        import shutil
        total, used, free = shutil.disk_usage("/opt/slot-booking")
        free_percent = (free / total) * 100

        if free_percent > 10:
            health_status["checks"]["disk_space"] = "ok"
        else:
            health_status["checks"]["disk_space"] = "warning"

        health_status["checks"]["free_space_percent"] = round(free_percent, 2)
    except Exception as e:
        health_status["checks"]["disk_space"] = f"error: {str(e)}"

    # Memory check
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()

        mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
        mem_available = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1])

        mem_usage_percent = ((mem_total - mem_available) / mem_total) * 100

        if mem_usage_percent < 90:
            health_status["checks"]["memory"] = "ok"
        else:
            health_status["checks"]["memory"] = "warning"

        health_status["checks"]["memory_usage_percent"] = round(mem_usage_percent, 2)
    except Exception as e:
        health_status["checks"]["memory"] = f"error: {str(e)}"

    return health_status

if __name__ == "__main__":
    health = check_health()
    print(json.dumps(health, indent=2))

    if health["status"] != "healthy":
        sys.exit(1)
EOF

    chmod +x $APP_DIR/health_check.py

    # Cron-Job für Health-Check-Monitoring
    (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/slot-booking/health_check.py > /opt/slot-booking/logs/health.log 2>&1") | crontab -

    log "Health check endpoint created ✓"
}

# ==================================================
# ANWENDUNG STARTEN
# ==================================================

start_application() {
    log "Starting Slot-Booking application..."

    # Service starten
    sudo systemctl start $SERVICE_NAME

    # Warten auf Startup
    sleep 5

    # Service-Status prüfen
    if systemctl is-active --quiet $SERVICE_NAME; then
        log "Application started successfully ✓"
    else
        error "Application failed to start. Check logs: sudo journalctl -u $SERVICE_NAME -f"
    fi

    # Health-Check durchführen
    info "Performing initial health check..."
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        log "Health check passed ✓"
    else
        warning "Health check failed - application may need more time to start"
    fi
}

# ==================================================
# POST-DEPLOYMENT TESTS
# ==================================================

run_tests() {
    log "Running post-deployment tests..."

    # HTTP-Response-Test
    info "Testing HTTP responses..."

    # Root endpoint
    if curl -f -s http://localhost/ > /dev/null; then
        echo "   ✅ Root endpoint responding"
    else
        echo "   ❌ Root endpoint failed"
    fi

    # Static files
    if curl -f -s http://localhost/static/style.css > /dev/null 2>&1; then
        echo "   ✅ Static files accessible"
    else
        echo "   ⚠️  Static files not found (may be normal)"
    fi

    # Application endpoints
    if curl -f -s http://localhost/login > /dev/null 2>&1; then
        echo "   ✅ Login endpoint responding"
    else
        echo "   ⚠️  Login endpoint not responding"
    fi

    # API endpoints
    if curl -f -s http://localhost/api/status > /dev/null 2>&1; then
        echo "   ✅ API endpoints responding"
    else
        echo "   ⚠️  API endpoints not found"
    fi

    # Performance-Test
    info "Testing response times..."
    response_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost/)
    echo "   Response time: ${response_time}s"

    # SSL-Test (falls konfiguriert)
    if curl -f -s https://localhost/ > /dev/null 2>&1; then
        echo "   ✅ HTTPS working"
    else
        echo "   ⚠️  HTTPS not configured or not working"
    fi

    log "Post-deployment tests completed ✓"
}

# ==================================================
# FINAL STATUS
# ==================================================

show_deployment_status() {
    log "=== DEPLOYMENT STATUS ==="

    echo ""
    info "🎯 Application Information:"
    echo "   Name: Slot-Booking Webapp"
    echo "   Location: $APP_DIR"
    echo "   User: $APP_USER"
    echo "   Service: $SERVICE_NAME"

    echo ""
    info "🌐 Access Information:"
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || echo 'N/A')
    echo "   Local URL: http://$LOCAL_IP/"
    echo "   External URL: http://$EXTERNAL_IP/"

    if [ -f "/etc/nginx/sites-enabled/slot-booking" ] && grep -q "ssl_certificate" /etc/nginx/sites-enabled/slot-booking 2>/dev/null; then
        echo "   HTTPS: Configured"
    else
        echo "   HTTPS: Not configured"
    fi

    echo ""
    info "⚙️  Service Status:"
    systemctl is-active $SERVICE_NAME && echo "   ✅ Application: Running" || echo "   ❌ Application: Not running"
    systemctl is-active nginx && echo "   ✅ Nginx: Running" || echo "   ❌ Nginx: Not running"
    systemctl is-active ssh && echo "   ✅ SSH: Running" || echo "   ❌ SSH: Not running"

    echo ""
    info "📊 System Resources:"
    echo "   CPU Load: $(cat /proc/loadavg | cut -d' ' -f1)"
    echo "   Memory: $(free -h | awk 'NR==2{printf "%.1f%%", $3/$2*100}')"
    echo "   Disk: $(df -h / | awk 'NR==2{print $5}') used"

    echo ""
    info "📁 Important Directories:"
    echo "   Application: $APP_DIR"
    echo "   Data: $APP_DIR/data"
    echo "   Logs: $APP_DIR/logs"
    echo "   Backups: /opt/backups"

    echo ""
    info "🔧 Management Commands:"
    echo "   Start: sudo systemctl start $SERVICE_NAME"
    echo "   Stop: sudo systemctl stop $SERVICE_NAME"
    echo "   Restart: sudo systemctl restart $SERVICE_NAME"
    echo "   Logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "   Status: sudo systemctl status $SERVICE_NAME"

    echo ""
    warning "🔒 Security Checklist:"
    echo "   [ ] Close SSH port 22 in Fritzbox after testing"
    echo "   [ ] Configure SSL certificate for domain"
    echo "   [ ] Set up monitoring and alerting"
    echo "   [ ] Test backup and restore procedures"
    echo "   [ ] Configure log retention policies"

    echo ""
    log "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
}

# ==================================================
# MAIN EXECUTION
# ==================================================

main() {
    log "Starting Slot-Booking Application Deployment..."

    echo ""
    warning "This script will deploy the complete Slot-Booking application:"
    echo "   - Clone application code from Git repository"
    echo "   - Install Python dependencies"
    echo "   - Configure environment variables"
    echo "   - Set up data migration"
    echo "   - Configure systemd service"
    echo "   - Set up Nginx reverse proxy"
    echo "   - Configure T2-Closer system"
    echo "   - Set up logging and monitoring"
    echo "   - Start application services"

    echo ""
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Deployment cancelled by user"
    fi

    echo ""
    log "Starting application deployment..."

    # Ausführungsreihenfolge
    check_prerequisites
    configure_environment
    deploy_application
    install_dependencies
    migrate_data
    configure_service
    configure_nginx
    setup_t2_system
    setup_logging
    create_health_check
    start_application
    run_tests

    echo ""
    show_deployment_status

    echo ""
    log "🎉 Application deployment completed successfully!"
    log "Slot-Booking webapp is now running and accessible!"

    echo ""
    info "📞 Next steps:"
    echo "   1. Test all application features"
    echo "   2. Configure SSL certificate if domain is available"
    echo "   3. Set up monitoring and alerting"
    echo "   4. Close SSH port in Fritzbox for security"
    echo "   5. Configure automated backups"
}

# Script starten
main "$@"