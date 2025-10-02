#!/bin/bash

# ========================================
# Business Tool Hub - Auto Deployment
# ========================================
#
# Automatisches Deployment zum VPS
# Nutzt Windows SSH-Key (~/.ssh/server_key)
#
# VERWENDUNG:
#   cd deployment
#   bash deploy.sh
#
# ========================================

set -e  # Exit bei Fehler

# ========================================
# KONFIGURATION
# ========================================

VPS_IP="91.98.192.233"
VPS_USER="root"
VPS_PATH="/opt/business-hub"
SSH_KEY="$HOME/.ssh/server_key"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

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

check_ssh_key() {
    if [[ ! -f "$SSH_KEY" ]]; then
        print_error "SSH-Key nicht gefunden: $SSH_KEY"
        print_info "Siehe: deployment/DEPLOY.md für SSH-Setup"
        exit 1
    fi
    print_success "SSH-Key gefunden"
}

test_connection() {
    print_info "Teste SSH-Verbindung..."
    if ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$VPS_USER@$VPS_IP" "echo 'OK'" &>/dev/null; then
        print_success "SSH-Verbindung OK"
    else
        print_error "SSH-Verbindung fehlgeschlagen!"
        print_info "Siehe: deployment/DEPLOY.md#ssh-zugang-setup"
        exit 1
    fi
}

# ========================================
# DEPLOYMENT
# ========================================

print_header "Business Tool Hub - Deployment"
print_info "VPS: $VPS_USER@$VPS_IP"
print_info "Path: $VPS_PATH"
echo ""

# Checks
check_ssh_key
test_connection

# ----------------------------------------
# 1. Backup erstellen
# ----------------------------------------
print_header "1. Backup erstellen"
BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S).tar.gz"
print_info "Erstelle Backup: $BACKUP_NAME"

ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" \
    "cd $VPS_PATH && tar -czf data/backups/$BACKUP_NAME app/ templates/ deployment/ 2>/dev/null || true"

BACKUP_SIZE=$(ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "ls -lh $VPS_PATH/data/backups/$BACKUP_NAME 2>/dev/null | awk '{print \$5}'" || echo "N/A")
print_success "Backup erstellt: $BACKUP_NAME ($BACKUP_SIZE)"

# ----------------------------------------
# 2. Core-Dateien hochladen
# ----------------------------------------
print_header "2. Core-Dateien hochladen"

cd ..  # Zurück ins Projekt-Root

print_info "Uploading app/__init__.py..."
scp -i "$SSH_KEY" app/__init__.py "$VPS_USER@$VPS_IP:$VPS_PATH/app/" &>/dev/null
print_success "app/__init__.py"

print_info "Uploading app/routes/auth.py..."
scp -i "$SSH_KEY" app/routes/auth.py "$VPS_USER@$VPS_IP:$VPS_PATH/app/routes/" &>/dev/null
print_success "app/routes/auth.py"

print_info "Uploading app/routes/admin/dashboard.py..."
scp -i "$SSH_KEY" app/routes/admin/dashboard.py "$VPS_USER@$VPS_IP:$VPS_PATH/app/routes/admin/" &>/dev/null
print_success "app/routes/admin/dashboard.py"

print_info "Uploading app/services/data_persistence.py..."
scp -i "$SSH_KEY" app/services/data_persistence.py "$VPS_USER@$VPS_IP:$VPS_PATH/app/services/" &>/dev/null
print_success "app/services/data_persistence.py"

# ----------------------------------------
# 3. Neue Route-Module
# ----------------------------------------
print_header "3. Neue Route-Module hochladen"

ROUTES=("api_gateway.py" "hub.py" "slots.py" "t2.py")
for route in "${ROUTES[@]}"; do
    if [[ -f "app/routes/$route" ]]; then
        print_info "Uploading app/routes/$route..."
        scp -i "$SSH_KEY" "app/routes/$route" "$VPS_USER@$VPS_IP:$VPS_PATH/app/routes/" &>/dev/null
        print_success "app/routes/$route"
    fi
done

# ----------------------------------------
# 4. Templates hochladen
# ----------------------------------------
print_header "4. Templates hochladen"

# Template-Verzeichnisse erstellen
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" \
    "mkdir -p $VPS_PATH/templates/{hub,slots,t2}" &>/dev/null

# Hub Templates
if [[ -d "templates/hub" ]]; then
    print_info "Uploading templates/hub/..."
    scp -i "$SSH_KEY" -r templates/hub/* "$VPS_USER@$VPS_IP:$VPS_PATH/templates/hub/" &>/dev/null
    print_success "templates/hub/ ($(ls templates/hub | wc -l) files)"
fi

# Slots Templates
if [[ -d "templates/slots" ]]; then
    print_info "Uploading templates/slots/..."
    scp -i "$SSH_KEY" -r templates/slots/* "$VPS_USER@$VPS_IP:$VPS_PATH/templates/slots/" &>/dev/null
    print_success "templates/slots/ ($(ls templates/slots | wc -l) files)"
fi

# T2 Templates
if [[ -d "templates/t2" ]]; then
    print_info "Uploading templates/t2/..."
    scp -i "$SSH_KEY" -r templates/t2/* "$VPS_USER@$VPS_IP:$VPS_PATH/templates/t2/" &>/dev/null
    print_success "templates/t2/ ($(ls templates/t2 | wc -l) files)"
fi

# ----------------------------------------
# 5. Deployment-Configs aktualisieren
# ----------------------------------------
print_header "5. Deployment-Configs aktualisieren"

print_info "Uploading business-hub.service..."
scp -i "$SSH_KEY" deployment/business-hub.service "$VPS_USER@$VPS_IP:/etc/systemd/system/business-hub.service" &>/dev/null
print_success "business-hub.service"

print_info "Uploading nginx.conf..."
scp -i "$SSH_KEY" deployment/nginx.conf "$VPS_USER@$VPS_IP:/etc/nginx/sites-available/business-hub" &>/dev/null
print_success "nginx.conf"

# ----------------------------------------
# 6. Service neu starten
# ----------------------------------------
print_header "6. Service neu starten"

print_info "Systemd daemon reload..."
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "systemctl daemon-reload" &>/dev/null
print_success "Daemon reloaded"

print_info "Restarting business-hub service..."
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "systemctl restart business-hub" || {
    print_error "Service restart fehlgeschlagen!"
    print_info "Prüfe Logs: journalctl -u business-hub -n 50"
    exit 1
}
print_success "Service restarted"

print_info "Warte 3 Sekunden..."
sleep 3

# ----------------------------------------
# 7. Status prüfen
# ----------------------------------------
print_header "7. Status prüfen"

SERVICE_STATUS=$(ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "systemctl is-active business-hub" || echo "failed")

if [[ "$SERVICE_STATUS" == "active" ]]; then
    print_success "Service läuft: $SERVICE_STATUS"

    # Detaillierte Status-Info
    ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "systemctl status business-hub --no-pager -l | head -20"

else
    print_error "Service läuft NICHT: $SERVICE_STATUS"
    print_info "Logs:"
    ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "journalctl -u business-hub -n 20 --no-pager"
    exit 1
fi

# ----------------------------------------
# 8. Route-Tests
# ----------------------------------------
print_header "8. Route-Tests"

ROUTES_TO_TEST=("/" "/hub" "/slots" "/t2" "/api")

for route in "${ROUTES_TO_TEST[@]}"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$VPS_IP$route" || echo "000")

    if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "302" ]]; then
        print_success "$route → $HTTP_CODE"
    else
        print_warning "$route → $HTTP_CODE (unexpected)"
    fi
done

# ========================================
# ZUSAMMENFASSUNG
# ========================================

print_header "Deployment abgeschlossen!"

echo -e "${GREEN}${BOLD}"
cat << "EOF"
   ____             _                      _
  |  _ \  ___ _ __ | | ___  _   _  ___  __| |
  | | | |/ _ \ '_ \| |/ _ \| | | |/ _ \/ _` |
  | |_| |  __/ |_) | | (_) | |_| |  __/ (_| |
  |____/ \___| .__/|_|\___/ \__, |\___|\__,_|
             |_|            |___/
EOF
echo -e "${NC}"

print_success "Deployment erfolgreich!"
echo ""
print_info "Website: http://$VPS_IP"
print_info "Backup: $BACKUP_NAME ($BACKUP_SIZE)"
print_info "Service: business-hub (active)"
echo ""
print_info "Nächste Schritte:"
echo "  - Website im Browser testen"
echo "  - Logs überwachen: ssh -i ~/.ssh/server_key root@$VPS_IP 'journalctl -u business-hub -f'"
echo "  - Bei Problemen Rollback: siehe deployment/DEPLOY.md#troubleshooting"
echo ""

exit 0
