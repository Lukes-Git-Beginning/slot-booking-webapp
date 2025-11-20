#!/bin/bash
#
# Redis Setup Script für Hetzner VPS
#
# Installiert Redis 7.x mit Persistence (AOF + RDB)
#
# Usage:
#   chmod +x scripts/setup_redis.sh
#   sudo ./scripts/setup_redis.sh

set -e  # Exit on error

echo "============================================"
echo "🔴 Redis Setup für Business-Hub"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Redis installieren
echo -e "${GREEN}📦 Schritt 1: Redis installieren...${NC}"
apt update
apt install -y redis-server

# 2. Redis konfigurieren
echo -e "${GREEN}⚙️ Schritt 2: Redis konfigurieren...${NC}"

# Backup original config
cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

# Neue Config erstellen
cat > /etc/redis/redis.conf <<'EOF'
# Redis Configuration für Business-Hub

# Network
bind 127.0.0.1 ::1
port 6379
timeout 0
tcp-keepalive 300

# General
daemonize yes
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16

# Persistence (RDB Snapshots)
save 900 1        # Nach 900s wenn mindestens 1 Key geändert
save 300 10       # Nach 300s wenn mindestens 10 Keys geändert
save 60 10000     # Nach 60s wenn mindestens 10000 Keys geändert
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Persistence (AOF - Append-Only-File)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
aof-load-truncated yes

# Memory Management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Security
# requirepass YOUR_REDIS_PASSWORD_HERE  # Uncomment & set password if needed

# Slow Log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Latency Monitor
latency-monitor-threshold 100

# Event Notification (für Flask-Session)
notify-keyspace-events Ex
EOF

# 3. Redis-Directory erstellen
echo -e "${GREEN}📁 Schritt 3: Redis-Directories erstellen...${NC}"
mkdir -p /var/lib/redis
chown redis:redis /var/lib/redis
chmod 770 /var/lib/redis

# 4. Service neu starten
echo -e "${GREEN}🚀 Schritt 4: Redis starten...${NC}"
systemctl restart redis-server
systemctl enable redis-server

# 5. Status prüfen
echo -e "${GREEN}✅ Schritt 5: Status prüfen...${NC}"
systemctl status redis-server --no-pager || true

# 6. Verbindung testen
echo -e "${GREEN}🔌 Schritt 6: Verbindung testen...${NC}"
redis-cli ping

# 7. Redis-Info anzeigen
echo ""
echo -e "${GREEN}📊 Redis-Informationen:${NC}"
redis-cli INFO server | grep redis_version
redis-cli INFO memory | grep used_memory_human
redis-cli INFO persistence | grep aof_enabled

# 8. Environment-Variable für .env generieren
echo ""
echo -e "${GREEN}✅ Redis Setup abgeschlossen!${NC}"
echo ""
echo -e "${YELLOW}📝 Füge folgende Zeilen zu /opt/business-hub/.env hinzu:${NC}"
echo ""
echo "# Redis Configuration"
echo "REDIS_URL=redis://localhost:6379/0"
echo "SESSION_TYPE=redis"
echo "SESSION_REDIS=redis://localhost:6379/0"
echo ""

# 9. Monitoring-Script erstellen (optional)
echo -e "${GREEN}📈 Erstelle Monitoring-Script...${NC}"
cat > /opt/business-hub/scripts/redis_monitor.sh <<'MONITORSCRIPT'
#!/bin/bash
# Redis Monitoring Script
echo "🔴 Redis Status:"
redis-cli INFO stats | grep -E "total_connections_received|total_commands_processed|instantaneous_ops_per_sec"
redis-cli INFO memory | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio"
redis-cli INFO persistence | grep -E "aof_enabled|rdb_last_save_time"
echo ""
echo "📊 Database Keys:"
redis-cli DBSIZE
MONITORSCRIPT

chmod +x /opt/business-hub/scripts/redis_monitor.sh

echo -e "${GREEN}✅ Monitoring-Script erstellt: /opt/business-hub/scripts/redis_monitor.sh${NC}"
echo ""
echo -e "${GREEN}🎉 Setup abgeschlossen!${NC}"
echo ""
echo "Next Steps:"
echo "  1. .env aktualisieren (siehe oben)"
echo "  2. Flask-Session auf Redis umstellen (app/__init__.py)"
echo "  3. Cache-Manager auf Redis umstellen (app/core/cache_manager.py)"
echo "  4. Service neu starten: systemctl restart business-hub"
echo ""
echo "Useful Commands:"
echo "  redis-cli                          # Redis CLI öffnen"
echo "  redis-cli MONITOR                  # Live-Monitoring"
echo "  redis-cli --stat                   # Stats anzeigen"
echo "  redis-cli INFO                     # Alle Infos"
echo "  /opt/business-hub/scripts/redis_monitor.sh  # Monitoring-Script"
echo ""
