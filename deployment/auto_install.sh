#!/bin/bash

# ========================================
# Business Tool Hub - Vollautomatische Installation
# ========================================
#
# Dieses Script installiert und konfiguriert den kompletten
# Business Tool Hub automatisch auf einem frischen Ubuntu-Server.
#
# VORAUSSETZUNGEN:
# - Ubuntu 20.04 LTS oder höher
# - Internet-Verbindung
# - Sudo-Rechte für ausführenden Benutzer
#
# VERWENDUNG:
#   curl -fsSL https://raw.githubusercontent.com/.../auto_install.sh | bash
#   ODER
#   wget -O - https://raw.githubusercontent.com/.../auto_install.sh | bash
#   ODER
#   bash auto_install.sh
#
# ========================================

set -e  # Exit bei Fehler

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/tmp/business-hub-install.log"
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
    if [[ $EUID -eq 0 ]]; then
        print_error "Bitte führe dieses Script NICHT als root aus!"
        print_info "Nutze stattdessen: bash auto_install.sh"
        exit 1
    fi
}

check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        print_info "Sudo-Rechte werden benötigt. Bitte Passwort eingeben:"
        sudo -v
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
    fi
}

# ========================================
# KONFIGURATION
# ========================================

# VPS Provider Detection
detect_vps_provider() {
    local provider="unknown"

    # Hetzner Cloud Detection
    if grep -qi "hetzner" /sys/class/dmi/id/sys_vendor 2>/dev/null || \
       grep -qi "hetzner" /sys/class/dmi/id/board_vendor 2>/dev/null; then
        provider="hetzner"
    # Strato Detection
    elif grep -qi "strato" /etc/hostname 2>/dev/null || \
         grep -qi "strato" /sys/class/dmi/id/sys_vendor 2>/dev/null; then
        provider="strato"
    # Netcup Detection
    elif grep -qi "netcup" /sys/class/dmi/id/sys_vendor 2>/dev/null; then
        provider="netcup"
    # Contabo Detection
    elif grep -qi "contabo" /sys/class/dmi/id/sys_vendor 2>/dev/null; then
        provider="contabo"
    # Render.com Detection
    elif [[ -d "/opt/render" ]]; then
        provider="render"
    # Generic VPS (KVM, etc.)
    elif [[ -d "/sys/class/dmi/id" ]]; then
        provider="generic-vps"
    fi

    echo "$provider"
}

VPS_PROVIDER=$(detect_vps_provider)

# Installation-Verzeichnis (provider-abhängig)
INSTALL_USER="${USER}"

# VPS-Standard: /opt/business-hub
# Legacy/Home-Server: /home/user/business-hub
if [[ "$VPS_PROVIDER" == "render" ]]; then
    # Render.com spezial
    INSTALL_DIR="/opt/render/project/src"
    APP_USER="render"
elif [[ "$VPS_PROVIDER" != "unknown" ]] && [[ "$VPS_PROVIDER" != "generic-vps" ]]; then
    # Dedizierte VPS (Hetzner, Strato, etc.)
    INSTALL_DIR="/opt/business-hub"
    APP_USER="business-hub"
else
    # Fallback: Home-Server oder unbekannt
    INSTALL_DIR="/home/${INSTALL_USER}/business-hub"
    APP_USER="business-hub"
fi

# Repository
REPO_URL="https://github.com/Lukes-Git-Beginning/slot-booking-webapp.git"

# ========================================
# PRE-FLIGHT CHECKS
# ========================================

print_header "Business Tool Hub - Automatische Installation"
print_info "Installation wird vorbereitet..."
echo ""

check_root
check_sudo
check_os

# VPS Provider anzeigen
print_header "VPS Provider Detection"
print_info "Erkannter Provider: $VPS_PROVIDER"
print_info "Installation-Verzeichnis: $INSTALL_DIR"
print_info "Application-User: $APP_USER"
echo ""

case "$VPS_PROVIDER" in
    hetzner)
        print_success "Hetzner Cloud detected - Optimierte Konfiguration wird verwendet"
        ;;
    strato)
        print_success "Strato VPS detected - Optimierte Konfiguration wird verwendet"
        ;;
    netcup)
        print_success "Netcup VPS detected - Optimierte Konfiguration wird verwendet"
        ;;
    contabo)
        print_success "Contabo VPS detected - Optimierte Konfiguration wird verwendet"
        ;;
    render)
        print_warning "Render.com detected - Dieses Script ist nicht für Render optimiert!"
        read -p "Trotzdem fortfahren? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        ;;
    generic-vps)
        print_info "Generisches VPS detected - Standard-Konfiguration wird verwendet"
        ;;
    *)
        print_warning "Provider konnte nicht erkannt werden - Standard-Konfiguration"
        ;;
esac

# Prüfe Internet-Verbindung
print_info "Prüfe Internet-Verbindung..."
if ! ping -c 1 google.com &> /dev/null; then
    print_error "Keine Internet-Verbindung verfügbar"
    exit 1
fi
print_success "Internet-Verbindung OK"

# Prüfe verfügbaren Speicherplatz
AVAILABLE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [[ $AVAILABLE_SPACE -lt 10 ]]; then
    print_error "Nicht genug Speicherplatz (benötigt: 10GB, verfügbar: ${AVAILABLE_SPACE}GB)"
    exit 1
fi
print_success "Speicherplatz OK (${AVAILABLE_SPACE}GB verfügbar)"

# ========================================
# INSTALLATION START
# ========================================

echo ""
print_header "Phase 1: System-Updates & Basis-Pakete"

print_info "Aktualisiere Paket-Listen..."
sudo apt-get update -qq

print_info "Installiere System-Updates (kann einige Minuten dauern)..."
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq

print_info "Installiere Basis-Pakete..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    git \
    curl \
    wget \
    ufw \
    htop \
    net-tools \
    certbot \
    python3-certbot-nginx

print_success "System-Updates und Basis-Pakete installiert"

# ========================================
# FIREWALL
# ========================================

print_header "Phase 2: Firewall-Konfiguration"

print_info "Konfiguriere UFW Firewall..."
sudo ufw --force disable  # Erst deaktivieren für saubere Konfiguration
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw --force enable

print_success "Firewall konfiguriert (Ports: 22, 80, 443)"

# ========================================
# BENUTZER & VERZEICHNISSE
# ========================================

print_header "Phase 3: Benutzer & Verzeichnisse"

# Erstelle Application-User (falls nicht vorhanden)
if ! id "$APP_USER" &>/dev/null; then
    print_info "Erstelle Benutzer: $APP_USER"
    sudo useradd -m -s /bin/bash "$APP_USER"
    sudo usermod -aG www-data "$APP_USER"
    print_success "Benutzer $APP_USER erstellt"
else
    print_info "Benutzer $APP_USER existiert bereits"
fi

# Erstelle Log-Verzeichnis
print_info "Erstelle Log-Verzeichnis..."
sudo mkdir -p /var/log/business-hub
sudo chown "$APP_USER:$APP_USER" /var/log/business-hub
sudo chmod 755 /var/log/business-hub

print_success "Verzeichnisse erstellt"

# ========================================
# CODE DEPLOYMENT
# ========================================

print_header "Phase 4: Code-Deployment"

# Prüfe ob Git-Repo bereits existiert
if [[ -d "$INSTALL_DIR/.git" ]]; then
    print_info "Repository existiert bereits, aktualisiere..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    print_info "Clone Repository..."
    if [[ -d "$INSTALL_DIR" ]]; then
        print_warning "Verzeichnis existiert bereits, wird gesichert..."
        sudo mv "$INSTALL_DIR" "${INSTALL_DIR}.backup.$(date +%s)"
    fi

    # Clone als aktueller User
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
print_success "Code-Deployment abgeschlossen"

# ========================================
# PYTHON ENVIRONMENT
# ========================================

print_header "Phase 5: Python-Umgebung"

print_info "Erstelle Virtual Environment..."
python3 -m venv venv

print_info "Aktiviere Virtual Environment..."
source venv/bin/activate

print_info "Upgrade pip..."
pip install --upgrade pip -q

print_info "Installiere Dependencies (kann 2-3 Minuten dauern)..."
pip install -r requirements.txt -q

print_success "Python-Umgebung konfiguriert"

# ========================================
# KONFIGURATION
# ========================================

print_header "Phase 6: Anwendungs-Konfiguration"

# Erstelle .env Datei wenn nicht vorhanden
if [[ ! -f .env ]]; then
    print_info "Erstelle .env Datei aus Template..."
    cp .env.example .env

    # Generiere SECRET_KEY
    print_info "Generiere SECRET_KEY..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/your-super-secret-key-here-change-this-now/$SECRET_KEY/" .env

    print_success ".env Datei erstellt"
    print_warning "WICHTIG: .env Datei muss noch manuell konfiguriert werden!"
    print_info "Editiere: nano $INSTALL_DIR/.env"
    echo ""
    print_info "Erforderliche Variablen:"
    echo "  - GOOGLE_CREDS_BASE64  (Google Service Account)"
    echo "  - CENTRAL_CALENDAR_ID  (Kalender-E-Mail)"
    echo "  - USERLIST             (Benutzer:Passwort Paare)"
    echo "  - CONSULTANTS          (Berater-Kalender)"
    echo "  - T2_CLOSERS           (T2-Closer-Kalender)"
    echo ""
else
    print_info ".env Datei existiert bereits"
fi

# Erstelle Datenverzeichnisse
print_info "Erstelle Datenverzeichnisse..."
mkdir -p data/persistent data/backups
chmod 755 data
chmod 700 data/persistent data/backups

print_success "Konfiguration abgeschlossen"

# ========================================
# SYSTEMD SERVICE
# ========================================

print_header "Phase 7: Systemd Service"

print_info "Kopiere Service-Datei..."
sudo cp deployment/business-hub.service /etc/systemd/system/

# Passe Pfade in Service-Datei an
print_info "Passe Pfade an..."
sudo sed -i "s|/home/business-hub/business-hub|$INSTALL_DIR|g" /etc/systemd/system/business-hub.service
sudo sed -i "s|User=business-hub|User=$INSTALL_USER|g" /etc/systemd/system/business-hub.service

print_info "Lade Systemd-Konfiguration neu..."
sudo systemctl daemon-reload

print_info "Aktiviere Service..."
sudo systemctl enable business-hub

# Service wird NICHT automatisch gestartet, da .env noch konfiguriert werden muss
print_warning "Service wird NICHT automatisch gestartet"
print_info "Nach .env-Konfiguration starten mit: sudo systemctl start business-hub"

print_success "Systemd Service konfiguriert"

# ========================================
# NGINX
# ========================================

print_header "Phase 8: Nginx-Konfiguration"

print_info "Kopiere Nginx-Konfiguration..."
sudo cp deployment/nginx.conf /etc/nginx/sites-available/business-hub

# Entferne SSL-Zeilen für initiales Setup (da noch kein Zertifikat)
print_info "Konfiguriere für HTTP (SSL später mit Certbot)..."
sudo sed -i 's/listen 443 ssl http2;/# listen 443 ssl http2;/g' /etc/nginx/sites-available/business-hub
sudo sed -i 's/ssl_certificate/#ssl_certificate/g' /etc/nginx/sites-available/business-hub

# Passe Pfade an
print_info "Passe Pfade an..."
sudo sed -i "s|/home/business-hub/business-hub|$INSTALL_DIR|g" /etc/nginx/sites-available/business-hub

# Aktiviere Site
print_info "Aktiviere Site..."
sudo ln -sf /etc/nginx/sites-available/business-hub /etc/nginx/sites-enabled/

# Deaktiviere default site
if [[ -f /etc/nginx/sites-enabled/default ]]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

# Teste Nginx-Konfiguration
print_info "Teste Nginx-Konfiguration..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    print_success "Nginx-Konfiguration gültig"

    print_info "Starte Nginx neu..."
    sudo systemctl restart nginx
    print_success "Nginx gestartet"
else
    print_error "Nginx-Konfiguration ungültig"
    sudo nginx -t
fi

print_success "Nginx konfiguriert"

# ========================================
# BACKUP-SYSTEM
# ========================================

print_header "Phase 9: Backup-System"

print_info "Mache Backup-Script ausführbar..."
chmod +x deployment/backup.sh

print_info "Richte Backup-Cron-Job ein..."
# Füge Cron-Job hinzu (nur wenn noch nicht vorhanden)
CRON_CMD="0 2 * * * $INSTALL_DIR/deployment/backup.sh"
(crontab -l 2>/dev/null | grep -v "backup.sh"; echo "$CRON_CMD") | crontab -

print_success "Backup-System konfiguriert (täglich um 2 Uhr)"

# ========================================
# PERMISSIONS
# ========================================

print_header "Phase 10: Permissions & Ownership"

print_info "Setze Ownership..."
sudo chown -R "$INSTALL_USER:www-data" "$INSTALL_DIR"

print_info "Setze Permissions..."
find "$INSTALL_DIR" -type d -exec chmod 755 {} \;
find "$INSTALL_DIR" -type f -exec chmod 644 {} \;
chmod +x deployment/*.sh
chmod 600 .env 2>/dev/null || true

print_success "Permissions gesetzt"

# ========================================
# ABSCHLUSS
# ========================================

print_header "Installation Abgeschlossen!"

echo ""
echo -e "${GREEN}${BOLD}✓ Business Tool Hub erfolgreich installiert!${NC}"
echo ""
echo -e "${YELLOW}${BOLD}Nächste Schritte:${NC}"
echo ""
echo "1. Konfiguriere .env Datei:"
echo -e "   ${BLUE}nano $INSTALL_DIR/.env${NC}"
echo ""
echo "2. Trage folgende Variablen ein:"
echo "   - GOOGLE_CREDS_BASE64"
echo "   - CENTRAL_CALENDAR_ID"
echo "   - USERLIST"
echo "   - CONSULTANTS"
echo "   - T2_CLOSERS"
echo ""
echo "3. Starte die Anwendung:"
echo -e "   ${BLUE}sudo systemctl start business-hub${NC}"
echo ""
echo "4. Prüfe den Status:"
echo -e "   ${BLUE}sudo systemctl status business-hub${NC}"
echo ""
echo "5. Teste die Anwendung:"
echo -e "   ${BLUE}curl http://localhost/${NC}"
echo -e "   ${BLUE}curl http://localhost/health${NC}"
echo ""
echo "6. Optional: SSL-Zertifikat einrichten (wenn Domain vorhanden):"
echo -e "   ${BLUE}sudo certbot --nginx -d deine-domain.de${NC}"
echo ""
echo -e "${YELLOW}Wichtige Pfade:${NC}"
echo "  Installation:  $INSTALL_DIR"
echo "  Logs:          /var/log/business-hub/"
echo "  Config:        $INSTALL_DIR/.env"
echo "  Service:       sudo systemctl status business-hub"
echo "  Nginx:         sudo systemctl status nginx"
echo ""
echo -e "${YELLOW}Backup:${NC}"
echo "  Manuell:       $INSTALL_DIR/deployment/backup.sh"
echo "  Automatisch:   Täglich um 2:00 Uhr"
echo ""
echo -e "${BLUE}Installation-Log:${NC} $LOG_FILE"
echo ""
echo -e "${GREEN}Happy Coding! 🚀${NC}"
echo ""