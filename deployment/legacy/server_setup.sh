#!/bin/bash
# ==================================================
# Slot-Booking Server Setup Script
# Für Chef-Server mit Ubuntu 22.04 LTS
# Ausführung über TeamViewer-Session
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
# SYSTEM-INFORMATIONEN
# ==================================================

check_system() {
    log "Checking system requirements..."

    # Ubuntu Version prüfen
    if ! lsb_release -d | grep -q "Ubuntu 22.04"; then
        error "This script requires Ubuntu 22.04 LTS"
    fi

    # Sudo-Rechte prüfen
    if [ "$EUID" -eq 0 ]; then
        error "Please run this script as regular user with sudo access, not as root"
    fi

    # Sudo ohne Passwort möglich?
    if ! sudo -n true 2>/dev/null; then
        error "User needs sudo access without password prompt"
    fi

    # Internet-Verbindung prüfen
    if ! ping -c 1 google.com &> /dev/null; then
        error "No internet connection available"
    fi

    # Freier Speicherplatz prüfen (mindestens 5GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then
        error "Not enough disk space. Need at least 5GB free"
    fi

    log "System checks passed ✓"
}

# ==================================================
# SYSTEM-UPDATE
# ==================================================

update_system() {
    log "Updating system packages..."

    sudo apt update -y
    sudo apt upgrade -y
    sudo apt autoremove -y
    sudo apt autoclean

    log "System updated ✓"
}

# ==================================================
# FIREWALL-KONFIGURATION
# ==================================================

setup_firewall() {
    log "Configuring firewall..."

    # UFW installieren falls nicht vorhanden
    sudo apt install -y ufw

    # UFW zurücksetzen
    sudo ufw --force reset

    # Default-Policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing

    # SSH erlauben (wichtig!)
    sudo ufw allow ssh
    sudo ufw allow 22/tcp

    # HTTP/HTTPS für Webserver
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp

    # Firewall aktivieren
    sudo ufw --force enable

    # Status anzeigen
    sudo ufw status verbose

    log "Firewall configured ✓"
}

# ==================================================
# NGINX WEBSERVER
# ==================================================

install_nginx() {
    log "Installing and configuring Nginx..."

    # Nginx installieren
    sudo apt install -y nginx

    # Nginx starten und aktivieren
    sudo systemctl start nginx
    sudo systemctl enable nginx

    # Nginx-Status prüfen
    if ! sudo systemctl is-active --quiet nginx; then
        error "Nginx failed to start"
    fi

    # Test-Seite erstellen
    sudo tee /var/www/html/index.html > /dev/null <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>Slot-Booking Server</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        .container { max-width: 600px; margin: 0 auto; }
        .status { color: green; font-size: 24px; }
        .info { color: #666; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Slot-Booking Server</h1>
        <p class="status">✅ Server is running!</p>
        <p class="info">Nginx Web Server configured successfully</p>
        <p class="info">Ready for application deployment</p>
        <hr>
        <p><small>Server IP: $(hostname -I | awk '{print $1}')</small></p>
        <p><small>Server Time: $(date)</small></p>
    </div>
</body>
</html>
EOF

    # Nginx-Konfiguration testen
    sudo nginx -t

    # Nginx neu laden
    sudo systemctl reload nginx

    log "Nginx installed and configured ✓"
}

# ==================================================
# SSL-ZERTIFIKAT (LET'S ENCRYPT)
# ==================================================

setup_ssl() {
    log "Setting up SSL certificates..."

    # Certbot installieren
    sudo apt install -y certbot python3-certbot-nginx

    # Domain-Name erfragen
    echo ""
    read -p "Enter domain name (e.g., slot-portal.hopto.org) or press Enter to skip SSL setup: " DOMAIN_NAME

    if [ -z "$DOMAIN_NAME" ]; then
        warning "Skipping SSL setup - can be configured later"
        return 0
    fi

    # Nginx-Konfiguration für Domain erstellen
    sudo tee /etc/nginx/sites-available/$DOMAIN_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;
    root /var/www/html;
    index index.html index.htm;

    location / {
        try_files \$uri \$uri/ =404;
    }

    # Location für Flask-App (später)
    location /app/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Site aktivieren
    sudo ln -sf /etc/nginx/sites-available/$DOMAIN_NAME /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default

    # Nginx-Konfiguration testen
    sudo nginx -t
    sudo systemctl reload nginx

    # SSL-Zertifikat anfordern
    info "Requesting SSL certificate for $DOMAIN_NAME..."
    info "Make sure domain points to this server's external IP!"

    read -p "Press Enter when domain DNS is configured correctly..."

    if sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME; then
        log "SSL certificate obtained and configured ✓"
    else
        warning "SSL certificate setup failed - can be retried later with: sudo certbot --nginx -d $DOMAIN_NAME"
    fi

    # Auto-Renewal testen
    sudo certbot renew --dry-run

    log "SSL setup completed ✓"
}

# ==================================================
# PYTHON-UMGEBUNG
# ==================================================

setup_python() {
    log "Setting up Python environment..."

    # Python 3.10+ und pip installieren
    sudo apt install -y python3 python3-pip python3-venv python3-dev

    # Python-Version prüfen
    python3_version=$(python3 --version | cut -d' ' -f2)
    info "Python version: $python3_version"

    # Virtuelle Umgebung für App erstellen
    sudo mkdir -p /opt/slot-booking
    sudo chown $USER:$USER /opt/slot-booking

    cd /opt/slot-booking
    python3 -m venv venv
    source venv/bin/activate

    # pip upgraden
    pip install --upgrade pip

    # Basis-Pakete installieren
    pip install wheel setuptools

    log "Python environment ready ✓"
}

# ==================================================
# SYSTEMD-SERVICE FÜR APP
# ==================================================

create_systemd_service() {
    log "Creating systemd service for Slot-Booking App..."

    # Systemd-Service-Datei erstellen
    sudo tee /etc/systemd/system/slot-booking.service > /dev/null <<EOF
[Unit]
Description=Slot-Booking Flask Application
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/slot-booking
Environment=PATH=/opt/slot-booking/venv/bin
ExecStart=/opt/slot-booking/venv/bin/python run.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=FLASK_ENV=production
Environment=PERSIST_BASE=/opt/slot-booking/data

[Install]
WantedBy=multi-user.target
EOF

    # Service laden
    sudo systemctl daemon-reload

    log "Systemd service created ✓"
}

# ==================================================
# MONITORING & TOOLS
# ==================================================

install_monitoring() {
    log "Installing monitoring tools..."

    # System-Monitoring-Tools
    sudo apt install -y htop iotop nethogs tree curl wget git

    # Log-Rotation konfigurieren
    sudo tee /etc/logrotate.d/slot-booking > /dev/null <<EOF
/opt/slot-booking/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload slot-booking
    endscript
}
EOF

    # Disk-Usage-Alert-Script
    sudo tee /usr/local/bin/disk-usage-alert.sh > /dev/null <<'EOF'
#!/bin/bash
THRESHOLD=85
USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

if [ $USAGE -gt $THRESHOLD ]; then
    echo "Warning: Disk usage is ${USAGE}% on $(hostname)"
    # Hier könnte E-Mail-Benachrichtigung hinzugefügt werden
fi
EOF

    sudo chmod +x /usr/local/bin/disk-usage-alert.sh

    # Cron-Job für Disk-Usage-Check
    (crontab -l 2>/dev/null; echo "0 */6 * * * /usr/local/bin/disk-usage-alert.sh") | crontab -

    log "Monitoring tools installed ✓"
}

# ==================================================
# BACKUP-SYSTEM
# ==================================================

setup_backup() {
    log "Setting up backup system..."

    # Backup-Verzeichnisse erstellen
    sudo mkdir -p /opt/backups/daily
    sudo mkdir -p /opt/backups/weekly
    sudo chown -R $USER:$USER /opt/backups

    # Backup-Script erstellen
    tee /opt/slot-booking/backup.sh > /dev/null <<'EOF'
#!/bin/bash
# Slot-Booking Backup Script

BACKUP_DIR="/opt/backups"
APP_DIR="/opt/slot-booking"
DATE=$(date +%Y%m%d_%H%M%S)

# Tägliches Backup
DAILY_BACKUP="$BACKUP_DIR/daily/backup_$DATE.tar.gz"

echo "Creating backup: $DAILY_BACKUP"

tar -czf "$DAILY_BACKUP" \
    --exclude="$APP_DIR/venv" \
    --exclude="$APP_DIR/logs/*.log" \
    -C "$APP_DIR" .

# Alte tägliche Backups löschen (älter als 7 Tage)
find "$BACKUP_DIR/daily" -name "backup_*.tar.gz" -mtime +7 -delete

# Wöchentliches Backup (Sonntags)
if [ $(date +%u) -eq 7 ]; then
    WEEKLY_BACKUP="$BACKUP_DIR/weekly/backup_weekly_$DATE.tar.gz"
    cp "$DAILY_BACKUP" "$WEEKLY_BACKUP"

    # Alte wöchentliche Backups löschen (älter als 4 Wochen)
    find "$BACKUP_DIR/weekly" -name "backup_weekly_*.tar.gz" -mtime +28 -delete
fi

echo "Backup completed: $DAILY_BACKUP"
EOF

    chmod +x /opt/slot-booking/backup.sh

    # Cron-Job für tägliche Backups (2:00 Uhr)
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/slot-booking/backup.sh") | crontab -

    log "Backup system configured ✓"
}

# ==================================================
# SSH-SICHERHEIT
# ==================================================

secure_ssh() {
    log "Hardening SSH configuration..."

    # SSH-Konfiguration sichern
    sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

    # Sichere SSH-Konfiguration
    sudo tee /etc/ssh/sshd_config > /dev/null <<EOF
# Slot-Booking Server SSH Configuration
Port 22
Protocol 2

# Authentication
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys

# Security
PermitEmptyPasswords no
MaxAuthTries 3
MaxSessions 10
LoginGraceTime 30

# Disable unused features
X11Forwarding no
PrintMotd no
TCPKeepAlive yes
ClientAliveInterval 300
ClientAliveCountMax 2

# Logging
SyslogFacility AUTH
LogLevel VERBOSE

# User restrictions
AllowUsers $USER

# Subsystem
Subsystem sftp /usr/lib/openssh/sftp-server
EOF

    # SSH-Konfiguration testen
    sudo sshd -t

    # SSH-Service neu starten
    sudo systemctl restart ssh

    log "SSH security hardened ✓"
}

# ==================================================
# FINAL SYSTEM STATUS
# ==================================================

show_status() {
    log "=== SYSTEM STATUS ==="

    echo ""
    info "🖥️  System Information:"
    echo "   OS: $(lsb_release -d | cut -f2)"
    echo "   Kernel: $(uname -r)"
    echo "   Uptime: $(uptime -p)"
    echo "   Load: $(cat /proc/loadavg | cut -d' ' -f1-3)"

    echo ""
    info "💾 Storage Information:"
    df -h / | tail -1 | awk '{print "   Root: " $3 " used, " $4 " available (" $5 " used)"}'
    df -h /data 2>/dev/null | tail -1 | awk '{print "   Data: " $3 " used, " $4 " available (" $5 " used)"}'

    echo ""
    info "🌐 Network Information:"
    echo "   Local IP: $(hostname -I | awk '{print $1}')"
    echo "   External IP: $(curl -s ifconfig.me 2>/dev/null || echo 'N/A')"

    echo ""
    info "🔥 Firewall Status:"
    sudo ufw status | grep -E "(Status|22|80|443)"

    echo ""
    info "⚙️  Service Status:"
    systemctl is-active nginx && echo "   ✅ Nginx: Running" || echo "   ❌ Nginx: Not running"
    systemctl is-active ssh && echo "   ✅ SSH: Running" || echo "   ❌ SSH: Not running"
    systemctl is-enabled slot-booking &>/dev/null && echo "   ✅ Slot-Booking: Enabled" || echo "   ⚠️  Slot-Booking: Not enabled yet"

    echo ""
    info "🔒 Security Status:"
    echo "   ✅ Firewall: Enabled"
    echo "   ✅ SSH: Hardened"
    echo "   ✅ Non-root user: $USER"

    echo ""
    warning "⚠️  Next Steps:"
    echo "   1. Deploy Slot-Booking application"
    echo "   2. Configure SSL certificate (if domain available)"
    echo "   3. Test application functionality"
    echo "   4. Close SSH port 22 in Fritzbox (after deployment)"

    echo ""
    log "=== SERVER SETUP COMPLETED ==="
}

# ==================================================
# DEPLOYMENT-VORBEREITUNG
# ==================================================

prepare_deployment() {
    log "Preparing for application deployment..."

    # App-Verzeichnis-Struktur erstellen
    mkdir -p /opt/slot-booking/logs
    mkdir -p /opt/slot-booking/data/persistent
    mkdir -p /opt/slot-booking/data/backups

    # Berechtigungen setzen
    chmod 755 /opt/slot-booking
    chmod 755 /opt/slot-booking/data

    # Git-Repository klonen (Platzhalter)
    info "Application deployment will require:"
    echo "   - Git repository clone"
    echo "   - Python dependencies installation"
    echo "   - Environment variables configuration"
    echo "   - Database/data migration"
    echo "   - Service activation"

    log "Deployment preparation completed ✓"
}

# ==================================================
# MAIN EXECUTION
# ==================================================

main() {
    log "Starting Slot-Booking Server Setup..."
    log "This will configure Ubuntu 22.04 LTS for production use"

    echo ""
    warning "This script will make significant changes to the system:"
    echo "   - Update all packages"
    echo "   - Configure firewall"
    echo "   - Install Nginx web server"
    echo "   - Set up SSL certificates"
    echo "   - Configure Python environment"
    echo "   - Install monitoring tools"
    echo "   - Set up backup system"
    echo "   - Harden SSH security"

    echo ""
    read -p "Continue with setup? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Setup cancelled by user"
    fi

    echo ""
    log "Starting system setup..."

    # Ausführungsreihenfolge
    check_system
    update_system
    setup_firewall
    install_nginx
    setup_ssl
    setup_python
    create_systemd_service
    install_monitoring
    setup_backup
    secure_ssh
    prepare_deployment

    echo ""
    show_status

    echo ""
    log "🎉 Server setup completed successfully!"
    log "Server is ready for Slot-Booking application deployment"

    echo ""
    info "📞 Ready for next phase:"
    echo "   - Application deployment via Git"
    echo "   - Database migration"
    echo "   - Service activation"
    echo "   - Final testing"
}

# Script starten
main "$@"