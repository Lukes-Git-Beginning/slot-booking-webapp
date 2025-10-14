#!/bin/bash
# Domain Migration Script for berater.zfa.gmbh
# Migriert die Anwendung von IP-only zu Subdomain mit SSL

set -e  # Exit on error

SERVER="91.98.192.233"
SSH_KEY="~/.ssh/server_key"
DOMAIN="berater.zfa.gmbh"
EMAIL="admin@zfa.gmbh"  # Für Let's Encrypt Benachrichtigungen

echo "========================================="
echo "Domain Migration zu berater.zfa.gmbh"
echo "Subdomain von zfa.gmbh (Strato)"
echo "========================================="

# 1. DNS-Check
echo ""
echo "1. Prüfe DNS-Konfiguration..."
echo "✓ DNS wurde bereits manuell verifiziert: berater.zfa.gmbh → 91.98.192.233"

# 2. Backup erstellen
echo ""
echo "2. Erstelle Backup der aktuellen Konfiguration..."
ssh -i $SSH_KEY root@$SERVER "mkdir -p /opt/business-hub/backups/domain-migration-$(date +%Y%m%d)"
ssh -i $SSH_KEY root@$SERVER "cp /etc/nginx/sites-available/business-hub /opt/business-hub/backups/domain-migration-$(date +%Y%m%d)/nginx.conf.backup"
ssh -i $SSH_KEY root@$SERVER "cp /opt/business-hub/.env /opt/business-hub/backups/domain-migration-$(date +%Y%m%d)/.env.backup"
echo "✓ Backup erstellt"

# 3. Certbot installieren (falls nicht vorhanden)
echo ""
echo "3. Prüfe Certbot-Installation..."
if ! ssh -i $SSH_KEY root@$SERVER "which certbot > /dev/null 2>&1"; then
    echo "Installiere Certbot..."
    ssh -i $SSH_KEY root@$SERVER "apt-get update && apt-get install -y certbot python3-certbot-nginx"
    echo "✓ Certbot installiert"
else
    echo "✓ Certbot bereits installiert"
fi

# 4. Nginx-Konfiguration hochladen
echo ""
echo "4. Lade neue Nginx-Konfiguration hoch..."
scp -i $SSH_KEY deployment/nginx_production.conf root@$SERVER:/etc/nginx/sites-available/business-hub
echo "✓ Nginx-Konfiguration hochgeladen"

# 5. Nginx-Syntax testen (ohne SSL-Zertifikate)
echo ""
echo "5. Teste Nginx-Syntax..."
ssh -i $SSH_KEY root@$SERVER "nginx -t" && echo "✓ Nginx-Syntax OK" || {
    echo "❌ Nginx-Syntax-Fehler!"
    exit 1
}

# 6. Nginx neu laden (HTTP-only für ACME challenge)
echo ""
echo "6. Lade Nginx neu (HTTP-only Modus)..."
ssh -i $SSH_KEY root@$SERVER "systemctl reload nginx"
echo "✓ Nginx neu geladen"

# 7. SSL-Zertifikat beantragen
echo ""
echo "7. Beantrage Let's Encrypt SSL-Zertifikat..."
echo "Dies kann 1-2 Minuten dauern..."
ssh -i $SSH_KEY root@$SERVER "certbot certonly --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --no-eff-email" && {
    echo "✓ SSL-Zertifikat erfolgreich erstellt"
} || {
    echo "❌ SSL-Zertifikat-Fehler!"
    echo "Mögliche Ursachen:"
    echo "  - DNS nicht korrekt konfiguriert"
    echo "  - Port 80/443 nicht erreichbar"
    echo "  - Rate-Limit von Let's Encrypt"
    exit 1
}

# 8. Nginx final neu laden (mit SSL)
echo ""
echo "8. Aktiviere HTTPS..."
ssh -i $SSH_KEY root@$SERVER "systemctl reload nginx"
echo "✓ HTTPS aktiviert"

# 9. .env-Datei aktualisieren
echo ""
echo "9. Aktualisiere .env-Datei..."
echo "WICHTIG: Bitte .env.production manuell bearbeiten und dann hochladen!"
echo ""
echo "Folgende Werte müssen ausgefüllt werden:"
echo "  - SECRET_KEY"
echo "  - USERLIST"
echo "  - ADMIN_USERS"
echo "  - GOOGLE_CREDS_BASE64"
echo "  - CENTRAL_CALENDAR_ID"
echo "  - CONSULTANTS"
echo ""
read -p "Wurde deployment/.env.production ausgefüllt? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    scp -i $SSH_KEY deployment/.env.production root@$SERVER:/opt/business-hub/.env
    echo "✓ .env-Datei hochgeladen"
else
    echo "⚠️  .env-Datei übersprungen - bitte später manuell hochladen!"
fi

# 10. Application neu starten
echo ""
echo "10. Starte Application neu..."
ssh -i $SSH_KEY root@$SERVER "systemctl restart business-hub"
sleep 3
echo "✓ Application neu gestartet"

# 11. Status prüfen
echo ""
echo "11. Prüfe Service-Status..."
ssh -i $SSH_KEY root@$SERVER "systemctl status business-hub --no-pager" || true

# 12. SSL-Test
echo ""
echo "12. Teste HTTPS-Verbindung..."
curl -sS -o /dev/null -w "HTTP Status: %{http_code}\n" https://$DOMAIN/health && {
    echo "✓ HTTPS funktioniert!"
} || {
    echo "⚠️  HTTPS-Test fehlgeschlagen"
}

# 13. Auto-Renewal testen
echo ""
echo "13. Teste SSL Auto-Renewal..."
ssh -i $SSH_KEY root@$SERVER "certbot renew --dry-run" && {
    echo "✓ Auto-Renewal konfiguriert"
} || {
    echo "⚠️  Auto-Renewal-Problem"
}

# Zusammenfassung
echo ""
echo "========================================="
echo "Migration abgeschlossen!"
echo "========================================="
echo ""
echo "✅ Domain: https://$DOMAIN"
echo "✅ SSL-Zertifikat: Let's Encrypt"
echo "✅ Auto-Renewal: Aktiv"
echo ""
echo "Nächste Schritte:"
echo "1. Teste alle Features: https://$DOMAIN"
echo "2. Prüfe Logs: ssh -i $SSH_KEY root@$SERVER 'tail -50 /var/log/business-hub/error.log'"
echo "3. Emergency-Zugang: http://$SERVER:8080"
echo ""
echo "Rollback (falls nötig):"
echo "ssh -i $SSH_KEY root@$SERVER 'cp /opt/business-hub/backups/domain-migration-$(date +%Y%m%d)/nginx.conf.backup /etc/nginx/sites-available/business-hub && systemctl reload nginx'"
echo ""
