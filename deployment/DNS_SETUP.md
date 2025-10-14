# DNS-Konfiguration für berater.zfa.gmbh

## Übersicht

Diese Anleitung beschreibt die notwendigen DNS-Einträge für den Produktiv-Betrieb der Business Hub Plattform.

**Domain-Info:**
- 🏢 **Provider:** Strato
- 🌐 **Hauptdomain:** zfa.gmbh (bei Strato)
- 📍 **Subdomain:** berater.zfa.gmbh (diese App)

---

## 🌐 Erforderliche DNS-Einträge

### 1. A-Records (IPv4) - FÜR SUBDOMAIN

**WICHTIG:** Da `berater.zfa.gmbh` eine **Subdomain** von `zfa.gmbh` ist, musst du im Strato DNS-Manager die Subdomain `berater` konfigurieren!

| Hostname | Type | Value | TTL | Beschreibung |
|----------|------|-------|-----|--------------|
| `berater` | A | `91.98.192.233` | 3600 | Subdomain für Business Hub |
| `www.berater` | A | `91.98.192.233` | 3600 | WWW-Variante (optional) |

**Strato-Konfiguration:**
```
Type: A
Subdomain: berater
Ziel/Value: 91.98.192.233
TTL: 3600 (Standard bei Strato: 1 Stunde)

Type: A (optional)
Subdomain: www.berater
Ziel/Value: 91.98.192.233
TTL: 3600
```

**Alternative (falls Strato volles FQDN verlangt):**
```
Type: A
Name: berater.zfa.gmbh
Ziel: 91.98.192.233
```

---

### 2. CAA-Record (SSL-Zertifikat-Autorisierung) - OPTIONAL

⚠️ **Strato unterstützt CAA-Records möglicherweise nicht!**

Falls verfügbar, konfigurieren:
```
Type: CAA
Subdomain: berater (oder leer für zfa.gmbh)
Tag: issue
Value: letsencrypt.org
TTL: 3600
```

**Falls nicht verfügbar:**
- Kein Problem! Let's Encrypt funktioniert auch ohne CAA-Record
- SSL-Zertifikat wird trotzdem ausgestellt
- Nur etwas weniger sicher (andere CAs könnten theoretisch auch Zertifikate ausstellen)

---

### 3. Optional: AAAA-Record (IPv6)

Falls Hetzner IPv6 bereitstellt:

```
Type: AAAA
Name: @
Value: [IPv6-Adresse vom Server]
TTL: 3600
```

**IPv6-Adresse ermitteln:**
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "ip -6 addr show scope global"
```

---

## 🔍 DNS-Verifizierung

### Nach Konfiguration der DNS-Einträge:

#### 1. DNS-Propagation prüfen (kann 24h dauern)

```bash
# Von lokalem PC aus
nslookup berater.zfa.gmbh 8.8.8.8
nslookup www.berater.zfa.gmbh 8.8.8.8

# Erwartetes Ergebnis:
# Name: berater.zfa.gmbh
# Address: 91.98.192.233
```

#### 2. Online-Tools nutzen

- **DNS Checker:** https://dnschecker.org/
  - Domain eingeben: `berater.zfa.gmbh`
  - Prüft DNS-Propagation weltweit

- **What's My DNS:** https://www.whatsmydns.net/
  - Domain eingeben: `berater.zfa.gmbh`
  - Zeigt DNS-Status in verschiedenen Regionen

#### 3. CAA-Record prüfen

```bash
dig CAA berater.zfa.gmbh

# Erwartetes Ergebnis:
# berater.zfa.gmbh. 3600 IN CAA 0 issue "letsencrypt.org"
```

---

## ⏱️ DNS-Propagation Timeline (Strato)

| Zeitpunkt | Status | Nächster Schritt |
|-----------|--------|------------------|
| **0h** | DNS-Einträge bei Strato erstellt | Strato-Bestätigung abwarten |
| **0.5-1h** | Strato aktiviert Änderungen | Erste Tests möglich |
| **1-4h** | DNS-Server aktualisiert | Migration kann gestartet werden ✅ |
| **4-8h** | Globale Propagation | Vollständig verfügbar |

**Strato ist schneller als 24h!** Meist nach 1-4 Stunden einsatzbereit.

---

## 🚀 Bereit für Migration?

Prüfe alle Punkte:

- [ ] A-Record für `berater.zfa.gmbh` → `91.98.192.233`
- [ ] A-Record für `www.berater.zfa.gmbh` → `91.98.192.233`
- [ ] CAA-Record für `berater.zfa.gmbh` → `letsencrypt.org`
- [ ] DNS-Propagation abgeschlossen (mind. 4h gewartet)
- [ ] `nslookup` zeigt korrekte IP
- [ ] `deployment/.env.production` ausgefüllt

**Wenn alle Punkte erfüllt sind:**

```bash
# Von lokalem PC aus
cd deployment
bash domain_migration.sh
```

---

## 🔧 DNS-Konfiguration bei Strato (EURE SITUATION)

### Schritt-für-Schritt Anleitung für Strato

**1. In Strato Kunden-Login einloggen**
   - https://www.strato.de/apps/CustomerService
   - Mit Kundennummer + Passwort anmelden

**2. Domain-Verwaltung öffnen**
   - **Domains** → **Domainverwaltung**
   - Domain `zfa.gmbh` auswählen

**3. DNS-Einstellungen / Subdomains**
   - **DNS-Einstellungen** oder **Subdomain verwalten**
   - Button: **Neue Subdomain anlegen** oder **A-Record hinzufügen**

**4. Subdomain `berater` erstellen**
   ```
   Subdomain: berater
   Typ: A-Record
   Ziel/IP: 91.98.192.233
   TTL: 3600 (Standard)
   ```

**5. Optional: WWW-Variante**
   ```
   Subdomain: www.berater
   Typ: A-Record
   Ziel/IP: 91.98.192.233
   TTL: 3600
   ```

**6. Speichern & Bestätigen**
   - Änderungen speichern
   - Bestätigungs-E-Mail abwarten (falls Strato das verlangt)

### Strato-spezifische Besonderheiten

- ⏱️ **Propagation-Zeit:** Bei Strato meist 1-4 Stunden (schneller als 24h)
- 🔄 **TTL:** Standard 3600s (1 Stunde), kann nicht immer geändert werden
- 📧 **Bestätigung:** Manche Änderungen benötigen E-Mail-Bestätigung
- 🚫 **CAA-Records:** Oft nicht verfügbar (kein Problem für Let's Encrypt)
- 📱 **Interface:** Strato hat oft 2 Interfaces (alt/neu) - nutze das neue

### Verifizierung nach Konfiguration

```bash
# Nach 1-2 Stunden testen
nslookup berater.zfa.gmbh 8.8.8.8

# Sollte zurückgeben:
# Name: berater.zfa.gmbh
# Address: 91.98.192.233
```

---

## 🔧 Andere Provider (für Referenz)

<details>
<summary>Cloudflare (klicken zum Ausklappen)</summary>

1. Einloggen → Domain auswählen
2. **DNS** → **Add record**
3. Einträge hinzufügen (siehe oben)
4. **Proxy status:** OFF (⚠️ WICHTIG für Let's Encrypt!)
5. **SSL/TLS:** Full (strict) nach Migration

</details>

<details>
<summary>Hetzner DNS</summary>

1. DNS Console → Zone auswählen
2. **Add Record**
3. Einträge wie oben hinzufügen
4. Nameserver prüfen: `ns1.hetzner.com`, `ns2.hetzner.com`, etc.

</details>

<details>
<summary>IONOS / 1&1</summary>

1. Domain-Verwaltung → DNS-Einstellungen
2. **A-Record hinzufügen**
3. Subdomain: `berater`
4. Ziel: `91.98.192.233`

</details>

---

## 🆘 Troubleshooting

### Problem: DNS zeigt falsche IP

```bash
# TTL abwarten (Zeit im DNS-Record, meist 3600s = 1h)
# Cache leeren
ipconfig /flushdns  # Windows
sudo dscacheutil -flushcache  # macOS
```

### Problem: CAA-Record nicht unterstützt

- Einige Provider unterstützen CAA-Records nicht
- In diesem Fall: Weglassen (weniger sicher, aber funktioniert)

### Problem: SSL-Zertifikat-Fehler trotz DNS

```bash
# Let's Encrypt Rate-Limits prüfen
curl https://letsencrypt.org/docs/rate-limits/

# Alternative: Staging-Modus testen
certbot certonly --nginx --staging -d berater.zfa.gmbh
```

---

## 📞 Support

Bei DNS-Problemen:
1. DNS-Provider-Support kontaktieren
2. Logs prüfen: `ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/nginx/error.log"`
3. Rollback möglich (siehe `domain_migration.sh`)

---

**Letzte Aktualisierung:** 2025-10-13
