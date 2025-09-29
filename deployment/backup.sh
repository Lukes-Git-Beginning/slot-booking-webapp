#!/bin/bash

# ========================================
# Business Tool Hub - Backup Script
# ========================================
#
# Dieses Script erstellt automatische Backups aller kritischen Daten
#
# Usage:
#   ./backup.sh                    # Manuelles Backup
#   crontab -e                     # Automatisierung
#   0 2 * * * /path/to/backup.sh   # Täglich um 2 Uhr nachts
#
# ========================================

set -e  # Exit bei Fehler

# Konfiguration
APP_DIR="/home/business-hub/business-hub"
DATA_DIR="$APP_DIR/data/persistent"
BACKUP_DIR="$APP_DIR/data/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="backup_$TIMESTAMP"
RETENTION_DAYS=30  # Backups älter als 30 Tage werden gelöscht

# Log-Datei
LOG_FILE="/var/log/business-hub/backup.log"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging-Funktion
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# ========================================
# Hauptfunktion
# ========================================

main() {
    log "=========================================="
    log "Starting Backup: $BACKUP_NAME"
    log "=========================================="

    # Prüfe ob Verzeichnisse existieren
    if [ ! -d "$DATA_DIR" ]; then
        error "Data directory not found: $DATA_DIR"
        exit 1
    fi

    # Erstelle Backup-Verzeichnis falls nicht vorhanden
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"

    # Erstelle Backup-Unterverzeichnis
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    mkdir -p "$BACKUP_PATH"

    # Backup: Persistent Data
    log "Backing up persistent data..."
    if [ -d "$DATA_DIR" ]; then
        cp -r "$DATA_DIR"/* "$BACKUP_PATH/" 2>/dev/null || true
        log "✓ Persistent data backed up"
    else
        warning "No persistent data found"
    fi

    # Backup: .env Konfiguration (ohne Passwörter im Klartext)
    log "Backing up configuration..."
    if [ -f "$APP_DIR/.env" ]; then
        # Erstelle .env Backup mit maskierten sensiblen Daten
        sed 's/\(SECRET_KEY\|PASSWORD\|CREDS\)=.*/\1=***MASKED***/g' "$APP_DIR/.env" > "$BACKUP_PATH/.env.backup"
        log "✓ Configuration backed up (credentials masked)"
    else
        warning "No .env file found"
    fi

    # Backup: Static files (availability.json etc.)
    log "Backing up static files..."
    if [ -d "$APP_DIR/static" ]; then
        mkdir -p "$BACKUP_PATH/static"
        cp "$APP_DIR/static"/*.json "$BACKUP_PATH/static/" 2>/dev/null || true
        log "✓ Static files backed up"
    fi

    # Erstelle Backup-Metadaten
    cat > "$BACKUP_PATH/backup_info.txt" <<EOF
Backup Information
==================
Timestamp: $(date)
Backup Name: $BACKUP_NAME
Server: $(hostname)
User: $(whoami)
Application Directory: $APP_DIR

Files Backed Up:
$(find "$BACKUP_PATH" -type f | wc -l) files
$(du -sh "$BACKUP_PATH" | cut -f1) total size

Data Files:
$(ls -lh "$BACKUP_PATH"/*.json 2>/dev/null | awk '{print $9, $5}' || echo "No JSON files")
EOF

    log "✓ Backup metadata created"

    # Komprimiere Backup
    log "Compressing backup..."
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME" 2>/dev/null || {
        error "Compression failed"
        exit 1
    }

    # Lösche unkomprimiertes Backup-Verzeichnis
    rm -rf "$BACKUP_PATH"

    BACKUP_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
    log "✓ Backup compressed: ${BACKUP_NAME}.tar.gz ($BACKUP_SIZE)"

    # Erstelle Symlink zum neuesten Backup
    ln -sf "${BACKUP_NAME}.tar.gz" "$BACKUP_DIR/latest.tar.gz"
    log "✓ Latest backup symlink updated"

    # Cleanup alte Backups
    log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

    OLD_COUNT=$(find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS | wc -l)
    if [ "$OLD_COUNT" -gt 0 ]; then
        log "✓ Deleted $OLD_COUNT old backup(s)"
    else
        log "✓ No old backups to delete"
    fi

    # Backup-Statistiken
    TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "backup_*.tar.gz" | wc -l)
    TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

    log "=========================================="
    log "Backup completed successfully!"
    log "Total backups: $TOTAL_BACKUPS"
    log "Total size: $TOTAL_SIZE"
    log "=========================================="

    # Optional: Gesundheitscheck nach Backup
    verify_backup "${BACKUP_NAME}.tar.gz"
}

# ========================================
# Backup-Verifizierung
# ========================================

verify_backup() {
    local backup_file="$1"
    log "Verifying backup integrity..."

    if tar -tzf "$BACKUP_DIR/$backup_file" > /dev/null 2>&1; then
        log "✓ Backup integrity verified"
        return 0
    else
        error "Backup verification failed!"
        return 1
    fi
}

# ========================================
# Restore-Funktion (für manuelles Restore)
# ========================================

restore_backup() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        error "Usage: $0 restore <backup_file.tar.gz>"
        exit 1
    fi

    if [ ! -f "$BACKUP_DIR/$backup_file" ]; then
        error "Backup file not found: $backup_file"
        exit 1
    fi

    warning "=========================================="
    warning "RESTORE OPERATION"
    warning "This will overwrite current data!"
    warning "Backup file: $backup_file"
    warning "=========================================="

    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log "Restore cancelled"
        exit 0
    fi

    log "Starting restore from: $backup_file"

    # Erstelle Backup der aktuellen Daten vor Restore
    log "Creating safety backup of current data..."
    SAFETY_BACKUP="safety_before_restore_$(date +%Y%m%d_%H%M%S)"
    cp -r "$DATA_DIR" "$BACKUP_DIR/$SAFETY_BACKUP" 2>/dev/null || true

    # Extract und Restore
    log "Extracting backup..."
    cd "$BACKUP_DIR"
    tar -xzf "$backup_file"

    EXTRACTED_DIR="${backup_file%.tar.gz}"

    log "Restoring data..."
    cp -r "$BACKUP_DIR/$EXTRACTED_DIR"/*.json "$DATA_DIR/" 2>/dev/null || true

    # Cleanup
    rm -rf "$EXTRACTED_DIR"

    log "✓ Restore completed!"
    log "Safety backup saved as: $SAFETY_BACKUP"

    warning "Please restart the application: sudo systemctl restart business-hub"
}

# ========================================
# Script Execution
# ========================================

# Prüfe Argumente
if [ "$1" = "restore" ]; then
    restore_backup "$2"
elif [ "$1" = "list" ]; then
    log "Available backups in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null || log "No backups found"
elif [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Business Tool Hub - Backup Script"
    echo ""
    echo "Usage:"
    echo "  $0              Create new backup"
    echo "  $0 restore <file>   Restore from backup"
    echo "  $0 list         List all backups"
    echo "  $0 help         Show this help"
    echo ""
    echo "Scheduled backups (cron):"
    echo "  0 2 * * * $0    # Daily at 2 AM"
else
    main
fi

exit 0