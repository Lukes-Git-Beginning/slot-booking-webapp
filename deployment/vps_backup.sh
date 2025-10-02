#!/bin/bash

# ========================================
# Business Tool Hub - VPS Backup Script
# ========================================
#
# Automatisches Backup-System für VPS-Deployment
# Funktioniert provider-unabhängig (Hetzner, Strato, etc.)
#
# VERWENDUNG:
#   ./vps_backup.sh [full|data|quick]
#
# BACKUP-TYPEN:
#   full  - Komplett-Backup (Code + Daten + Config)
#   data  - Nur Daten-Backup (schnell)
#   quick - Nur kritische Daten
#
# CRON-SETUP:
#   # Täglich um 2 Uhr
#   0 2 * * * /usr/local/bin/vps_backup.sh data >> /var/log/business-hub/backup.log 2>&1
#
# ========================================

set -e  # Exit bei Fehler

# ========================================
# KONFIGURATION
# ========================================

APP_NAME="business-hub"
APP_DIR="/opt/business-hub"
BACKUP_BASE_DIR="/opt/business-hub/backups"
BACKUP_RETENTION_DAYS=30
MAX_BACKUPS=10

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Backup-Typ (default: data)
BACKUP_TYPE="${1:-data}"

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_BASE_DIR}/${BACKUP_TYPE}_${TIMESTAMP}"

# ========================================
# FUNKTIONEN
# ========================================

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
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

check_requirements() {
    # App-Verzeichnis prüfen
    if [ ! -d "$APP_DIR" ]; then
        print_error "Application-Verzeichnis nicht gefunden: $APP_DIR"
        exit 1
    fi

    # Backup-Verzeichnis erstellen
    mkdir -p "$BACKUP_BASE_DIR"

    # tar verfügbar?
    if ! command -v tar &> /dev/null; then
        print_error "tar nicht gefunden!"
        exit 1
    fi

    print_success "Requirements erfüllt"
}

get_backup_size() {
    local dir=$1
    du -sh "$dir" 2>/dev/null | awk '{print $1}'
}

# ========================================
# BACKUP-FUNKTIONEN
# ========================================

backup_data_persistent() {
    print_info "Backup: Persistente Daten..."

    if [ -d "$APP_DIR/data/persistent" ]; then
        cp -r "$APP_DIR/data/persistent" "$BACKUP_DIR/persistent"
        local count=$(ls -1 "$APP_DIR/data/persistent" | wc -l)
        print_success "Persistente Daten gesichert ($count Dateien)"
    else
        print_warning "Persistent-Verzeichnis nicht gefunden"
    fi
}

backup_static_data() {
    print_info "Backup: Static-Daten (Legacy-Fallback)..."

    if [ -d "$APP_DIR/static" ]; then
        mkdir -p "$BACKUP_DIR/static"
        cp "$APP_DIR"/static/*.json "$BACKUP_DIR/static/" 2>/dev/null || true
        print_success "Static-Daten gesichert"
    fi
}

backup_config() {
    print_info "Backup: Konfigurationsdateien..."

    mkdir -p "$BACKUP_DIR/config"

    # .env Datei (WICHTIG!)
    if [ -f "$APP_DIR/.env" ]; then
        cp "$APP_DIR/.env" "$BACKUP_DIR/config/.env"
        print_success ".env gesichert"
    else
        print_warning ".env nicht gefunden"
    fi

    # Service Account (falls vorhanden)
    if [ -f "$APP_DIR/service_account.json" ]; then
        cp "$APP_DIR/service_account.json" "$BACKUP_DIR/config/service_account.json"
        print_success "service_account.json gesichert"
    fi

    # Nginx Config
    if [ -f "/etc/nginx/sites-available/${APP_NAME}" ]; then
        cp "/etc/nginx/sites-available/${APP_NAME}" "$BACKUP_DIR/config/nginx.conf"
        print_success "Nginx-Config gesichert"
    fi

    # Systemd Service
    if [ -f "/etc/systemd/system/${APP_NAME}.service" ]; then
        cp "/etc/systemd/system/${APP_NAME}.service" "$BACKUP_DIR/config/systemd.service"
        print_success "Systemd-Service gesichert"
    fi
}

backup_logs() {
    print_info "Backup: Logs (letzte 7 Tage)..."

    mkdir -p "$BACKUP_DIR/logs"

    # Application Logs
    if [ -d "/var/log/${APP_NAME}" ]; then
        find "/var/log/${APP_NAME}" -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/logs/" \;
        print_success "Application-Logs gesichert"
    fi

    # Nginx Logs (nur Errors)
    if [ -f "/var/log/nginx/${APP_NAME}-error.log" ]; then
        tail -n 1000 "/var/log/nginx/${APP_NAME}-error.log" > "$BACKUP_DIR/logs/nginx-error.log"
        print_success "Nginx-Error-Logs gesichert"
    fi
}

backup_code() {
    print_info "Backup: Application-Code..."

    mkdir -p "$BACKUP_DIR/code"

    # Git-Info
    if [ -d "$APP_DIR/.git" ]; then
        cd "$APP_DIR"
        git log -1 --format="%H%n%an%n%ae%n%ad%n%s" > "$BACKUP_DIR/code/git-info.txt"
        git diff > "$BACKUP_DIR/code/git-diff.txt" || true
        print_success "Git-Info gesichert"
    fi

    # requirements.txt
    if [ -f "$APP_DIR/requirements.txt" ]; then
        cp "$APP_DIR/requirements.txt" "$BACKUP_DIR/code/requirements.txt"
    fi

    # Installed packages
    if [ -f "$APP_DIR/venv/bin/pip" ]; then
        "$APP_DIR/venv/bin/pip" list > "$BACKUP_DIR/code/pip-list.txt"
        print_success "Python-Packages gesichert"
    fi
}

backup_database() {
    print_info "Backup: Database-Export (JSON)..."

    # JSON-basiert, bereits in data/persistent enthalten
    print_success "Database bereits in persistent-Daten"
}

create_metadata() {
    print_info "Backup: Metadata erstellen..."

    cat > "$BACKUP_DIR/BACKUP_INFO.txt" << EOF
========================================
Business Tool Hub - Backup Metadata
========================================

Backup-Typ:       ${BACKUP_TYPE}
Backup-Zeit:      $(date)
Hostname:         $(hostname)
Server-IP:        $(hostname -I | awk '{print $1}')

Application:
  Verzeichnis:    ${APP_DIR}
  Service:        ${APP_NAME}
  Status:         $(systemctl is-active ${APP_NAME} 2>/dev/null || echo "unknown")

System:
  OS:             $(lsb_release -d | cut -f2)
  Kernel:         $(uname -r)
  Uptime:         $(uptime -p)
  RAM:            $(free -h | awk '/^Mem:/ {print $3 " / " $2}')
  Disk:           $(df -h / | awk 'NR==2 {print $3 " / " $2 " (" $5 " used)"}')

Backup-Inhalt:
EOF

    # Backup-Struktur
    tree -L 2 "$BACKUP_DIR" >> "$BACKUP_DIR/BACKUP_INFO.txt" 2>/dev/null || \
    find "$BACKUP_DIR" -maxdepth 2 -type f >> "$BACKUP_DIR/BACKUP_INFO.txt"

    # Backup-Größe
    echo "" >> "$BACKUP_DIR/BACKUP_INFO.txt"
    echo "Backup-Größe:" >> "$BACKUP_DIR/BACKUP_INFO.txt"
    du -sh "$BACKUP_DIR"/* >> "$BACKUP_DIR/BACKUP_INFO.txt"

    print_success "Metadata erstellt"
}

compress_backup() {
    print_info "Backup komprimieren..."

    local archive_name="${BACKUP_BASE_DIR}/${APP_NAME}_${BACKUP_TYPE}_${TIMESTAMP}.tar.gz"

    cd "$BACKUP_BASE_DIR"
    tar -czf "$archive_name" "$(basename $BACKUP_DIR)"

    local size=$(get_backup_size "$archive_name")
    print_success "Backup komprimiert: $size"

    # Unkomprimiertes Verzeichnis löschen
    rm -rf "$BACKUP_DIR"

    echo "$archive_name"
}

cleanup_old_backups() {
    print_info "Alte Backups bereinigen..."

    # Nach Datum löschen (älter als BACKUP_RETENTION_DAYS)
    find "$BACKUP_BASE_DIR" -name "${APP_NAME}_*.tar.gz" -mtime +${BACKUP_RETENTION_DAYS} -delete

    # Nach Anzahl löschen (behalte nur MAX_BACKUPS)
    local backup_count=$(ls -1 "$BACKUP_BASE_DIR"/${APP_NAME}_${BACKUP_TYPE}_*.tar.gz 2>/dev/null | wc -l)

    if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
        local to_delete=$((backup_count - MAX_BACKUPS))
        ls -1t "$BACKUP_BASE_DIR"/${APP_NAME}_${BACKUP_TYPE}_*.tar.gz | tail -n $to_delete | xargs rm -f
        print_success "$to_delete alte Backups gelöscht"
    else
        print_success "Keine alten Backups zum Löschen"
    fi

    # Verbleibende Backups
    local remaining=$(ls -1 "$BACKUP_BASE_DIR"/${APP_NAME}_*.tar.gz 2>/dev/null | wc -l)
    print_info "Verbleibende Backups: $remaining"
}

# ========================================
# BACKUP-TYPEN
# ========================================

backup_quick() {
    print_header "Quick Backup (nur kritische Daten)"

    mkdir -p "$BACKUP_DIR"

    backup_data_persistent
    backup_config
    create_metadata

    local archive=$(compress_backup)
    local size=$(get_backup_size "$archive")

    print_success "Quick-Backup abgeschlossen: $size"
}

backup_data_only() {
    print_header "Data Backup (Daten + Config)"

    mkdir -p "$BACKUP_DIR"

    backup_data_persistent
    backup_static_data
    backup_config
    backup_database
    create_metadata

    local archive=$(compress_backup)
    local size=$(get_backup_size "$archive")

    print_success "Data-Backup abgeschlossen: $size"
}

backup_full() {
    print_header "Full Backup (Alles)"

    mkdir -p "$BACKUP_DIR"

    backup_data_persistent
    backup_static_data
    backup_config
    backup_logs
    backup_code
    backup_database
    create_metadata

    local archive=$(compress_backup)
    local size=$(get_backup_size "$archive")

    print_success "Full-Backup abgeschlossen: $size"
}

# ========================================
# RESTORE-FUNKTIONEN (Info)
# ========================================

show_restore_info() {
    cat << 'EOF'

========================================
  Backup-Restore Anleitung
========================================

Um ein Backup wiederherzustellen:

1. Backup-Archiv entpacken:
   tar -xzf business-hub_data_20240101_120000.tar.gz

2. Service stoppen:
   systemctl stop business-hub

3. Daten wiederherstellen:
   cp -r backup_dir/persistent/* /opt/business-hub/data/persistent/
   cp backup_dir/config/.env /opt/business-hub/.env

4. Permissions korrigieren:
   chown -R business-hub:www-data /opt/business-hub/data/

5. Service starten:
   systemctl start business-hub

6. Verifikation:
   systemctl status business-hub
   curl http://localhost:5000/health

========================================

EOF
}

# ========================================
# MAIN
# ========================================

print_header "Business Tool Hub - Backup System"
print_info "Backup-Typ: $BACKUP_TYPE"
print_info "Timestamp: $TIMESTAMP"

check_requirements

case "$BACKUP_TYPE" in
    full)
        backup_full
        ;;
    data)
        backup_data_only
        ;;
    quick)
        backup_quick
        ;;
    *)
        print_error "Ungültiger Backup-Typ: $BACKUP_TYPE"
        echo ""
        echo "Verwendung: $0 [full|data|quick]"
        echo ""
        echo "  full  - Komplett-Backup (Code + Daten + Config + Logs)"
        echo "  data  - Daten-Backup (Daten + Config)"
        echo "  quick - Quick-Backup (nur kritische Daten)"
        exit 1
        ;;
esac

cleanup_old_backups

print_success "Alle Backups in: $BACKUP_BASE_DIR"
ls -lh "$BACKUP_BASE_DIR"/${APP_NAME}_*.tar.gz 2>/dev/null || echo "Keine Backups gefunden"

show_restore_info

print_success "Backup-Prozess abgeschlossen! ✓"