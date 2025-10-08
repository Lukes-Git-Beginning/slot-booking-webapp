#!/bin/bash
# Encrypted Backup Script for Business Hub
# Creates encrypted backups and pushes to Git repository

set -e

BACKUP_DIR="/opt/business-hub/backups"
DATA_DIR="/opt/business-hub/data/persistent"
REPO_DIR="/opt/business-hub"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"
ENCRYPTION_PASSWORD_FILE="/root/.business-hub-backup-key"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if encryption key exists
if [ ! -f "$ENCRYPTION_PASSWORD_FILE" ]; then
    error "Encryption key not found at $ENCRYPTION_PASSWORD_FILE"
    error "Run: openssl rand -base64 32 > $ENCRYPTION_PASSWORD_FILE && chmod 600 $ENCRYPTION_PASSWORD_FILE"
    exit 1
fi

log "Starting encrypted backup process..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Create backup archive
log "Creating backup archive..."
cd "$REPO_DIR"
tar -czf "${TEMP_DIR}/${BACKUP_NAME}.tar.gz" \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='node_modules' \
    data/persistent/ \
    .env 2>/dev/null || true

# Get archive size
ARCHIVE_SIZE=$(du -h "${TEMP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
log "Archive created: ${BACKUP_NAME}.tar.gz (${ARCHIVE_SIZE})"

# Encrypt the archive using AES-256-CBC
log "Encrypting backup..."
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
    -in "${TEMP_DIR}/${BACKUP_NAME}.tar.gz" \
    -out "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz.enc" \
    -pass file:"$ENCRYPTION_PASSWORD_FILE"

if [ $? -eq 0 ]; then
    ENCRYPTED_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz.enc" | cut -f1)
    log "Encrypted backup created: ${BACKUP_NAME}.tar.gz.enc (${ENCRYPTED_SIZE})"
else
    error "Encryption failed!"
    exit 1
fi

# Clean up old encrypted backups (keep last 30 days)
log "Cleaning old encrypted backups (>30 days)..."
find "$BACKUP_DIR" -name "backup_*.tar.gz.enc" -type f -mtime +30 -delete
REMAINING=$(find "$BACKUP_DIR" -name "backup_*.tar.gz.enc" -type f | wc -l)
log "Encrypted backups remaining: $REMAINING"

# Optional: Push to Git (if configured)
if git -C "$REPO_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    log "Checking Git repository..."

    cd "$REPO_DIR"

    # Check if there are changes to commit
    if [ -n "$(git status --porcelain backups/*.enc 2>/dev/null)" ]; then
        log "Committing encrypted backup to Git..."

        git add backups/*.enc
        git commit -m "backup: Add encrypted backup ${BACKUP_NAME}" || warn "Nothing to commit"

        # Push to remote (if configured)
        if git remote | grep -q "origin"; then
            log "Pushing to remote repository..."
            if git push origin main 2>/dev/null || git push origin master 2>/dev/null; then
                log "✓ Backup successfully pushed to Git remote"
            else
                warn "Could not push to remote (check credentials)"
            fi
        else
            warn "No Git remote configured, skipping push"
        fi
    else
        log "No new backups to commit"
    fi
else
    warn "Not a Git repository, skipping Git operations"
fi

log "✓ Encrypted backup completed successfully!"
log "Backup location: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz.enc"

# Instructions for decryption
log ""
log "To decrypt this backup:"
log "  openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \\"
log "    -in ${BACKUP_NAME}.tar.gz.enc \\"
log "    -out ${BACKUP_NAME}.tar.gz \\"
log "    -pass file:${ENCRYPTION_PASSWORD_FILE}"
log "  tar -xzf ${BACKUP_NAME}.tar.gz"

exit 0
