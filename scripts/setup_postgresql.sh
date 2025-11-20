#!/bin/bash
#
# PostgreSQL Setup Script für Hetzner VPS
#
# Installiert PostgreSQL 16, erstellt Database und User
#
# Usage:
#   chmod +x scripts/setup_postgresql.sh
#   sudo ./scripts/setup_postgresql.sh

set -e  # Exit on error

echo "============================================"
echo "🐘 PostgreSQL Setup für Business-Hub"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variablen
DB_NAME="business_hub"
DB_USER="business_hub_user"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24)}"  # Auto-generate if not set

echo -e "${YELLOW}ℹ️ Configuration:${NC}"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo ""

# 1. PostgreSQL installieren
echo -e "${GREEN}📦 Schritt 1: PostgreSQL installieren...${NC}"
apt update
apt install -y postgresql postgresql-contrib

# 2. Service starten
echo -e "${GREEN}🚀 Schritt 2: PostgreSQL starten...${NC}"
systemctl start postgresql
systemctl enable postgresql

# 3. Status prüfen
echo -e "${GREEN}✅ Schritt 3: Status prüfen...${NC}"
systemctl status postgresql --no-pager || true

# 4. Database und User erstellen
echo -e "${GREEN}🔐 Schritt 4: Database und User erstellen...${NC}"
sudo -u postgres psql <<EOF
-- Database erstellen
CREATE DATABASE $DB_NAME;

-- User erstellen
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Rechte vergeben
GRANT ALL PRIVILEGES ON DATABASE $DB_USER TO $DB_USER;

-- Für PostgreSQL 15+ (Public Schema Privileges)
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

-- User-Liste anzeigen
\du

-- Database-Liste anzeigen
\l

EOF

# 5. Connection testen
echo -e "${GREEN}🔌 Schritt 5: Verbindung testen...${NC}"
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -h localhost -c "SELECT version();"

# 6. Environment-Variable für .env generieren
echo ""
echo -e "${GREEN}✅ PostgreSQL Setup abgeschlossen!${NC}"
echo ""
echo -e "${YELLOW}📝 Füge folgende Zeilen zu /opt/business-hub/.env hinzu:${NC}"
echo ""
echo "# PostgreSQL Configuration"
echo "USE_POSTGRES=true"
echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"
echo ""
echo -e "${YELLOW}💾 Speichere das Passwort sicher!${NC}"
echo ""

# 7. Backup-Script erstellen (optional)
echo -e "${GREEN}📦 Erstelle Backup-Script...${NC}"
cat > /opt/business-hub/scripts/backup_postgres.sh <<'BACKUPSCRIPT'
#!/bin/bash
# PostgreSQL Backup Script
BACKUP_DIR="/opt/business-hub/data/backups/postgres"
DB_NAME="business_hub"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
pg_dump -U business_hub_user $DB_NAME | gzip > $BACKUP_DIR/backup_${DATE}.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "✅ Backup created: backup_${DATE}.sql.gz"
BACKUPSCRIPT

chmod +x /opt/business-hub/scripts/backup_postgres.sh

echo -e "${GREEN}✅ Backup-Script erstellt: /opt/business-hub/scripts/backup_postgres.sh${NC}"
echo ""
echo -e "${GREEN}🎉 Setup abgeschlossen!${NC}"
echo ""
echo "Next Steps:"
echo "  1. .env aktualisieren (siehe oben)"
echo "  2. Alembic Migrations ausführen: alembic upgrade head"
echo "  3. Migration-Script ausführen: python scripts/migrate_json_to_postgres.py --dry-run"
echo ""
