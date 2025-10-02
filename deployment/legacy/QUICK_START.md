# Business Tool Hub - Quick Start Guide

**Für erfahrene Admins: Die Essentials in 10 Minuten**

---

## 🚀 Express-Installation

```bash
# 1. System vorbereiten
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx git

# 2. User und Directory
sudo useradd -m -s /bin/bash business-hub
sudo su - business-hub
cd ~ && git clone <repo-url> business-hub && cd business-hub

# 3. Python Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Konfiguration
cp .env.example .env
nano .env  # SECRET_KEY, GOOGLE_CREDS_BASE64, USERLIST eintragen

# 5. Verzeichnisse
mkdir -p data/persistent data/backups

# 6. Service einrichten
exit  # Zurück zu root
sudo cp deployment/business-hub.service /etc/systemd/system/
sudo systemctl enable --now business-hub

# 7. Nginx konfigurieren
sudo cp deployment/nginx.conf /etc/nginx/sites-available/business-hub
sudo ln -s /etc/nginx/sites-available/business-hub /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# 8. SSL (optional, empfohlen)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d ihre-domain.de
```

---

## ⚙️ Minimale .env Konfiguration

```bash
SECRET_KEY=<python3 -c "import secrets; print(secrets.token_hex(32))">
GOOGLE_CREDS_BASE64=<base64 -w 0 service_account.json>
CENTRAL_CALENDAR_ID=zentralkalenderzfa@gmail.com
USERLIST=admin:secure_password,user1:pass1
ADMIN_USERS=admin
FLASK_ENV=production
```

---

## 🔍 Health Check

```bash
curl http://localhost/health
# Erwartete Antwort: {"status": "healthy", ...}
```

---

## 📝 Wichtigste Befehle

```bash
# Service Management
sudo systemctl restart business-hub
sudo systemctl status business-hub
sudo journalctl -u business-hub -f

# Nginx
sudo nginx -t
sudo systemctl reload nginx

# Logs
tail -f /var/log/business-hub/app.log
```

---

## ✅ Fertig!

Anwendung sollte erreichbar sein: **https://ihre-domain.de**

Für Details siehe: `INSTALLATION.md`