#!/bin/bash

# ========================================
# Business Tool Hub - VPS Setup Script
# ========================================
#
# Universelles Setup-Script für Ubuntu-basierte VPS
# Funktioniert auf: Hetzner, Strato, Netcup, Contabo, etc.
#
# VORAUSSETZUNGEN:
# - Ubuntu 20.04 LTS oder höher
# - Root-Zugriff oder sudo-Rechte
# - Mindestens 2GB RAM
# - Mindestens 10GB freier Speicher
#
# VERWENDUNG:
#   bash vps_setup.sh
#
# ========================================

set -e  # Exit bei Fehler

# ========================================
# KONFIGURATION
# ========================================

APP_NAME="business-hub"
APP_USER="business-hub"
APP_DIR="/opt/business-hub"
REPO_URL="https://github.com/yourusername/slot-booking-webapp.git"  # ANPASSEN!
PYTHON_VERSION="3.11"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Logging
LOG_FILE="/tmp/${APP_NAME}-setup.log"
exec > >(tee -a "$LOG_FILE")
exec 2>&1

# ========================================
# FUNKTIONEN
# ========================================

print_header() {
    echo -e "\n${BLUE}${BOLD}========================================${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING: $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Dieses Script muss als root ausgeführt werden!"
        print_info "Verwende: sudo bash vps_setup.sh"
        exit 1
    fi
}

check_os() {
    if [[ ! -f /etc/os-release ]]; then
        print_error "Konnte OS nicht erkennen"
        exit 1
    fi

    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]] && [[ "$ID" != "debian" ]]; then
        print_warning "Dieses Script ist für Ubuntu/Debian optimiert"
        print_info "Gefunden: $ID $VERSION_ID"
        read -p "Trotzdem fortfahren? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "OS erkannt: $ID $VERSION_ID"
    fi
}

check_resources() {
    # RAM prüfen
    total_ram=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$total_ram" -lt 1800 ]; then
        print_warning "Nur ${total_ram}MB RAM verfügbar (empfohlen: 2048MB)"
        read -p "Trotzdem fortfahren? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "RAM verfügbar: ${total_ram}MB"
    fi

    # Speicher prüfen
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 10000000 ]; then
        print_warning "Nur ${available_space}KB Speicher verfügbar"
    else
        print_success "Speicher verfügbar: $((available_space / 1024 / 1024))GB"
    fi
}

# ========================================
# INSTALLATION
# ========================================

print_header "Business Tool Hub - VPS Setup"
print_info "Starte Installation auf $(hostname)"
print_info "Log-Datei: $LOG_FILE"

# Checks
check_root
check_os
check_resources

# ----------------------------------------
# 1. System-Updates
# ----------------------------------------
print_header "1. System-Updates"
print_info "Aktualisiere Paketlisten..."
apt-get update -qq

print_info "Installiere System-Updates..."
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq

print_info "Installiere grundlegende Tools..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    curl \
    wget \
    git \
    vim \
    htop \
    ufw \
    build-essential \
    software-properties-common \
    unzip

print_success "System aktualisiert"

# ----------------------------------------
# 2. Python Installation
# ----------------------------------------
print_header "2. Python $PYTHON_VERSION Installation"

if command -v python${PYTHON_VERSION} &> /dev/null; then
    print_success "Python ${PYTHON_VERSION} bereits installiert"
else
    print_info "Installiere Python ${PYTHON_VERSION}..."
    add-apt-repository ppa:deadsnakes/ppa -y
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        python3-pip

    print_success "Python ${PYTHON_VERSION} installiert"
fi

# Symlink für python3
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1
print_success "Python3 Symlink erstellt"

# ----------------------------------------
# 3. Nginx Installation
# ----------------------------------------
print_header "3. Nginx Webserver Installation"

if command -v nginx &> /dev/null; then
    print_success "Nginx bereits installiert"
else
    print_info "Installiere Nginx..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx
    print_success "Nginx installiert"
fi

# Nginx starten
systemctl enable nginx
systemctl start nginx
print_success "Nginx aktiviert und gestartet"

# ----------------------------------------
# 4. Firewall (UFW)
# ----------------------------------------
print_header "4. Firewall-Konfiguration"

print_info "Konfiguriere UFW Firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS

print_success "Firewall konfiguriert"
ufw status

# ----------------------------------------
# 5. Application User
# ----------------------------------------
print_header "5. Application-User erstellen"

if id "$APP_USER" &>/dev/null; then
    print_success "User '$APP_USER' existiert bereits"
else
    print_info "Erstelle User '$APP_USER'..."
    useradd -r -m -s /bin/bash -d /home/$APP_USER $APP_USER
    print_success "User '$APP_USER' erstellt"
fi

# ----------------------------------------
# 6. Verzeichnisse
# ----------------------------------------
print_header "6. Verzeichnisstruktur erstellen"

print_info "Erstelle Verzeichnisse..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/data/persistent
mkdir -p $APP_DIR/data/backups
mkdir -p $APP_DIR/logs
mkdir -p /var/log/$APP_NAME

# Permissions
chown -R $APP_USER:www-data $APP_DIR
chmod 755 $APP_DIR
chmod 700 $APP_DIR/data/persistent
chmod 755 $APP_DIR/logs
chown -R $APP_USER:www-data /var/log/$APP_NAME

print_success "Verzeichnisse erstellt und Permissions gesetzt"

# ----------------------------------------
# 7. Repository klonen (Optional - kann auch manuell)
# ----------------------------------------
print_header "7. Application Code"

if [ -d "$APP_DIR/.git" ]; then
    print_success "Repository bereits geklont"
else
    print_info "Repository-URL: $REPO_URL"
    print_warning "Bitte manuell klonen mit:"
    echo "  sudo -u $APP_USER git clone $REPO_URL $APP_DIR"
    echo ""
fi

# ----------------------------------------
# 8. SSL/TLS (Certbot)
# ----------------------------------------
print_header "8. SSL/TLS Setup (Certbot)"

if command -v certbot &> /dev/null; then
    print_success "Certbot bereits installiert"
else
    print_info "Installiere Certbot..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        certbot \
        python3-certbot-nginx
    print_success "Certbot installiert"
fi

print_info "SSL-Zertifikat anfordern mit:"
echo "  sudo certbot --nginx -d deine-domain.de"
echo ""

# ----------------------------------------
# 9. Log Rotation
# ----------------------------------------
print_header "9. Log Rotation konfigurieren"

cat > /etc/logrotate.d/$APP_NAME << EOF
/var/log/$APP_NAME/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $APP_USER www-data
    sharedscripts
    postrotate
        systemctl reload $APP_NAME > /dev/null 2>&1 || true
    endscript
}
EOF

print_success "Log Rotation konfiguriert"

# ----------------------------------------
# 10. System Limits
# ----------------------------------------
print_header "10. System Limits optimieren"

cat >> /etc/security/limits.conf << EOF
# Business Tool Hub Limits
$APP_USER soft nofile 65536
$APP_USER hard nofile 65536
EOF

print_success "System Limits optimiert"

# ----------------------------------------
# 11. Monitoring Tools
# ----------------------------------------
print_header "11. Monitoring-Tools installieren"

DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    htop \
    iotop \
    nethogs \
    ncdu

print_success "Monitoring-Tools installiert"

# ----------------------------------------
# 12. Auto-Updates (optional)
# ----------------------------------------
print_header "12. Automatische Sicherheitsupdates"

DEBIAN_FRONTEND=noninteractive apt-get install -y -qq unattended-upgrades

cat > /etc/apt/apt.conf.d/50unattended-upgrades << EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}";
    "\${distro_id}:\${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

print_success "Automatische Sicherheitsupdates aktiviert"

# ========================================
# ZUSAMMENFASSUNG
# ========================================

print_header "Installation abgeschlossen!"

echo -e "${GREEN}${BOLD}"
cat << "EOF"
   ___           _        _ _       _   _
  |_ _|_ __  ___| |_ __ _| | | __ _| |_(_) ___  _ __
   | || '_ \/ __| __/ _` | | |/ _` | __| |/ _ \| '_ \
   | || | | \__ \ || (_| | | | (_| | |_| | (_) | | | |
  |___|_| |_|___/\__\__,_|_|_|\__,_|\__|_|\___/|_| |_|

   _____ _   _ ___ ____   ____ _   _
  |  ___| | | |_ _/ ___| / ___| | | |
  | |_  | |_| || | |  _  | |  _| | | |
  |  _| |  _  || | |_| | | |_| |_|_|_|
  |_|   |_| |_|___\____|  \____(_|_|_)

EOF
echo -e "${NC}"

print_success "Server-Setup abgeschlossen!"
echo ""
print_info "Nächste Schritte:"
echo ""
echo "  1. Application-Code deployen:"
echo "     sudo -u $APP_USER git clone <repo-url> $APP_DIR"
echo ""
echo "  2. .env Datei konfigurieren:"
echo "     sudo -u $APP_USER nano $APP_DIR/.env"
echo ""
echo "  3. Python Dependencies installieren:"
echo "     cd $APP_DIR"
echo "     sudo -u $APP_USER python3 -m venv venv"
echo "     sudo -u $APP_USER venv/bin/pip install -r requirements.txt"
echo ""
echo "  4. Systemd Service einrichten:"
echo "     cp $APP_DIR/deployment/business-hub.service /etc/systemd/system/"
echo "     systemctl daemon-reload"
echo "     systemctl enable $APP_NAME"
echo "     systemctl start $APP_NAME"
echo ""
echo "  5. Nginx konfigurieren:"
echo "     cp $APP_DIR/deployment/nginx.conf /etc/nginx/sites-available/$APP_NAME"
echo "     # Domain anpassen in der Datei!"
echo "     ln -s /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/"
echo "     nginx -t"
echo "     systemctl reload nginx"
echo ""
echo "  6. SSL-Zertifikat anfordern:"
echo "     certbot --nginx -d deine-domain.de"
echo ""
print_info "Log-Datei: $LOG_FILE"
print_info "Support: https://github.com/yourusername/slot-booking-webapp/issues"
echo ""
print_success "Happy Deploying! 🚀"