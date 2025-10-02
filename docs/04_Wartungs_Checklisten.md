# Wartungs-Checklisten
## Slot-Booking Server - Langfristige Betreuung

---

## 🎯 **Übersicht**
Strukturierte Checklisten für die regelmäßige Wartung und Überwachung des Slot-Booking Servers. Aufgeteilt nach Häufigkeit und Verantwortlichkeiten.

**Zielgruppe:** Chef (Basis-Wartung) + Remote-Support (Erweitert)
**Zeitaufwand:** 5-30 Minuten je nach Intervall

---

## 📋 **TÄGLICH (5 Minuten)**

### **🟢 Chef kann selbst erledigen:**

#### **System-Status visuell prüfen:**
- [ ] **Server-LEDs:** Power-LED leuchtet grün
- [ ] **Router-LEDs:** Internet-LED grün, LAN-LED am Server-Port
- [ ] **Monitor-Test:** Kurz am Server anmelden → `slotadmin` Login testen
- [ ] **Website-Check:** Browser → `http://192.168.178.100` → Lädt die Slot-Booking-Seite?

#### **Schnell-Test durchführen:**
```bash
# Einfache Kommandos für Chef:
ping 192.168.178.100     # Server antwortet?
curl http://192.168.178.100    # Website antwortet?
```

#### **Problem-Indikatoren:**
- ❌ **Server nicht erreichbar** → Sofort Remote-Support kontaktieren
- ❌ **Website lädt nicht** → Notieren und Remote-Support informieren
- ❌ **Sehr langsam** → Performance-Problem → Remote-Support

### **Dokumentation:**
- [ ] **Status-Log führen:** Einfache Excel/Word-Datei mit Datum + Status
- [ ] **Probleme notieren:** Uhrzeit, Symptome, was getan wurde

---

## 📋 **WÖCHENTLICH (15 Minuten)**

### **🟢 Chef kann selbst erledigen:**

#### **Internet-Geschwindigkeit testen:**
- [ ] **Speedtest:** https://speedtest.net → Mindestens 150/150 Mbit?
- [ ] **Andere Geräte:** WLAN-Geschwindigkeit auf Handy/PC normal?
- [ ] **Router-Status:** Fritzbox → `http://fritz.box` → Online-Monitor prüfen

#### **Grundlegende System-Checks:**
```bash
# SSH zum Server (falls möglich):
ssh slotadmin@192.168.178.100

# Einfache Status-Checks:
df -h          # Festplatten-Speicher (unter 80% = gut)
free -h        # RAM-Speicher
uptime         # Wie lange läuft der Server?
```

#### **Visuelle Inspektion:**
- [ ] **Staubentfernung:** Server-Lüftungsschlitze sauber?
- [ ] **Kabel-Check:** Alle Kabel fest angeschlossen?
- [ ] **Temperatur:** Server-Gehäuse nicht ungewöhnlich heiß?

### **🔴 Remote-Support erforderlich:**

#### **Erweiterte System-Checks:**
- [ ] **Service-Status:** Alle kritischen Services laufen?
- [ ] **Log-Analyse:** Fehler-Logs auf Probleme prüfen
- [ ] **Performance-Monitoring:** CPU/RAM/Disk-Usage normal?
- [ ] **Security-Scan:** Verdächtige Netzwerk-Aktivitäten?

#### **Backup-Verifikation:**
- [ ] **Backup-Prozess:** Automatische Backups laufen?
- [ ] **Backup-Größe:** Plausible Datenmengen?
- [ ] **Restore-Test:** Stichproben-Wiederherstellung

---

## 📋 **MONATLICH (30 Minuten)**

### **🟢 Chef kann teilweise erledigen:**

#### **Hardware-Wartung:**
- [ ] **Staub entfernen:** Server-Gehäuse öffnen und aussaugen
- [ ] **Festplatten-Check:** Ungewöhnliche Geräusche?
- [ ] **RAM-Test:** System stabil? Keine Abstürze?
- [ ] **Temperatur-Monitoring:** Lüfter arbeiten normal?

#### **Router-Wartung:**
- [ ] **Fritzbox-Updates:** Firmware-Version aktuell?
- [ ] **Neustart:** Router einmal komplett neu starten
- [ ] **Port-Check:** Freigaben noch korrekt?
- [ ] **Performance-Test:** Upload/Download-Geschwindigkeit messen

### **🔴 Remote-Support erforderlich:**

#### **System-Updates:**
- [ ] **Ubuntu-Updates:** `sudo apt update && sudo apt upgrade`
- [ ] **Python-Packages:** Requirements.txt auf Updates prüfen
- [ ] **Nginx-Updates:** Webserver auf aktuellem Stand?
- [ ] **Security-Patches:** Kritische Sicherheitsupdates installieren

#### **Application-Maintenance:**
- [ ] **Database-Cleanup:** Alte Daten archivieren
- [ ] **Log-Rotation:** Log-Dateien bereinigen
- [ ] **Performance-Tuning:** Langsame Queries optimieren
- [ ] **Feature-Updates:** Neue Funktionen deployen

#### **Security-Audit:**
- [ ] **SSH-Logs:** Verdächtige Login-Versuche?
- [ ] **Firewall-Rules:** UFW-Konfiguration aktuell?
- [ ] **SSL-Zertifikate:** Läuft automatische Erneuerung?
- [ ] **Port-Scan:** Externe Sicherheitsprüfung

#### **Backup-Management:**
- [ ] **Backup-Rotation:** Alte Backups bereinigen
- [ ] **Storage-Usage:** Backup-Speicher ausreichend?
- [ ] **Restore-Test:** Vollständige Wiederherstellung testen
- [ ] **Off-Site-Backup:** Cloud-Backup konfigurieren

---

## 📋 **VIERTELJÄHRLICH (1-2 Stunden)**

### **🔴 Remote-Support erforderlich:**

#### **Umfassende System-Analyse:**
- [ ] **Performance-Audit:** System-Bottlenecks identifizieren
- [ ] **Capacity-Planning:** Speicher/RAM-Bedarf prognostizieren
- [ ] **Network-Analysis:** Bandbreiten-Usage analysieren
- [ ] **Application-Metrics:** User-Verhalten und Performance-KPIs

#### **Security-Hardening:**
- [ ] **Vulnerability-Scan:** System auf Sicherheitslücken prüfen
- [ ] **Access-Review:** SSH-Keys und Benutzer-Accounts auditieren
- [ ] **Firewall-Audit:** Regel-Set auf Notwendigkeit prüfen
- [ ] **SSL-Security:** Zertifikat-Konfiguration optimieren

#### **Disaster-Recovery-Test:**
- [ ] **Full-Restore:** Komplette System-Wiederherstellung testen
- [ ] **Failover-Procedures:** Notfall-Prozeduren dokumentieren
- [ ] **Data-Recovery:** Datenverlust-Szenarien durchspielen
- [ ] **Documentation-Update:** Wartungs-Dokumente aktualisieren

#### **Feature-Development:**
- [ ] **User-Feedback:** Neue Anforderungen evaluieren
- [ ] **Technology-Updates:** Framework-Updates planen
- [ ] **Performance-Optimization:** Code-Optimierungen implementieren
- [ ] **Scalability-Planning:** Zukunfts-Architektur planen

---

## 📋 **JÄHRLICH (4-8 Stunden)**

### **🔴 Remote-Support erforderlich:**

#### **Hardware-Lifecycle-Management:**
- [ ] **Hardware-Health:** Festplatten-SMART-Status analysieren
- [ ] **Performance-Benchmarks:** System-Performance messen
- [ ] **Upgrade-Planning:** Hardware-Upgrades evaluieren
- [ ] **EOL-Planning:** End-of-Life-Strategien entwickeln

#### **Software-Lifecycle-Management:**
- [ ] **OS-Upgrade:** Ubuntu LTS-Upgrades planen
- [ ] **Framework-Updates:** Flask/Python-Major-Updates
- [ ] **Database-Migration:** Datenbankstruktur-Updates
- [ ] **API-Versioning:** Breaking-Changes koordinieren

#### **Business-Continuity:**
- [ ] **SLA-Review:** Service-Level-Agreements überprüfen
- [ ] **Cost-Analysis:** Betriebskosten analysieren
- [ ] **Risk-Assessment:** Geschäftsrisiken bewerten
- [ ] **Growth-Planning:** Skalierungs-Roadmap erstellen

---

## 🚨 **NOTFALL-CHECKLISTEN**

### **Server komplett ausgefallen:**

#### **🟢 Chef - Sofort-Maßnahmen (5 Minuten):**
1. **Hardware-Check:**
   - [ ] Stromkabel angeschlossen?
   - [ ] Power-Button 10 Sekunden gedrückt halten
   - [ ] 1 Minute warten, dann neu starten
   - [ ] LEDs leuchten nach Neustart?

2. **Netzwerk-Check:**
   - [ ] Router läuft normal?
   - [ ] LAN-Kabel fest angeschlossen?
   - [ ] Anderen LAN-Port am Router versuchen

3. **Dokumentation:**
   - [ ] Uhrzeit des Ausfalls notieren
   - [ ] Symptome beschreiben
   - [ ] Was wurde vor Ausfall gemacht?

4. **Remote-Support kontaktieren:**
   - [ ] **SOFORT** Luke anrufen/schreiben
   - [ ] Alle Symptome mitteilen
   - [ ] Auf Anweisungen warten

#### **🔴 Remote-Support - Erweiterte Diagnose:**
1. **Remote-Zugang versuchen:**
   - [ ] SSH-Verbindung testen
   - [ ] TeamViewer-Verbindung versuchen
   - [ ] Ping-Tests durchführen

2. **Hardware-Diagnose:**
   - [ ] BIOS-POST-Codes analysieren
   - [ ] RAM/Festplatten-Status prüfen
   - [ ] Systemd-Journal analysieren

3. **Service-Recovery:**
   - [ ] Services einzeln neu starten
   - [ ] Konfiguration wiederherstellen
   - [ ] Backup-Restore falls nötig

---

### **Website nicht erreichbar:**

#### **🟢 Chef - Basis-Checks (3 Minuten):**
1. **Lokaler Test:**
   - [ ] `http://192.168.178.100` im Browser
   - [ ] Andere Geräte im Netzwerk testen
   - [ ] Internet generell verfügbar?

2. **Router-Status:**
   - [ ] Fritzbox-Interface erreichbar?
   - [ ] Port-Freigaben noch aktiv?
   - [ ] Internet-Verbindung grün?

#### **🔴 Remote-Support - Service-Diagnose:**
1. **Service-Status:**
   - [ ] Nginx läuft?
   - [ ] Flask-App läuft?
   - [ ] SSL-Zertifikat gültig?

2. **Log-Analyse:**
   - [ ] Nginx error.log prüfen
   - [ ] Application-Logs analysieren
   - [ ] System-Logs durchsuchen

---

### **Performance-Probleme:**

#### **🟢 Chef - Performance-Check:**
1. **Basis-Metriken:**
   - [ ] Speedtest durchführen
   - [ ] Andere Anwendungen normal?
   - [ ] Server-Gehäuse heiß?

#### **🔴 Remote-Support - Detailanalyse:**
1. **System-Resources:**
   - [ ] CPU-Usage analysieren
   - [ ] RAM-Verbrauch prüfen
   - [ ] Disk-I/O messen
   - [ ] Network-Latenz testen

2. **Application-Performance:**
   - [ ] Database-Queries optimieren
   - [ ] Cache-Hit-Rates prüfen
   - [ ] Memory-Leaks identifizieren

---

## 📞 **KONTAKT-INFORMATIONEN**

### **Basis-Support (Chef):**
- **Tägliche Checks:** ✅ Kann Chef selbst
- **Hardware-Probleme:** ✅ Basis-Troubleshooting
- **Router-Neustart:** ✅ Kann Chef selbst
- **Strom/Kabel:** ✅ Kann Chef selbst

### **Remote-Support (Luke):**
- **Telefon:** [Nummer] (24/7 bei Notfällen)
- **SSH-Zugang:** `ssh slotadmin@192.168.178.100`
- **TeamViewer:** Nach Bedarf
- **E-Mail:** Für nicht-kritische Themen

### **Eskalation bei Notfällen:**
1. **Geschäftszeiten:** Anruf + SMS + E-Mail
2. **Außerhalb:** Nur Anruf bei kritischen Ausfällen
3. **Wochenende:** Nur bei kompletten System-Ausfällen

---

## 📊 **MONITORING-DASHBOARD**

### **🟢 Chef - Einfache Übersicht:**

#### **Täglich prüfen:**
```
Status-Ampel:
🟢 Server erreichbar
🟢 Website lädt
🟢 Internet-Geschwindigkeit OK
🟢 Keine Fehlermeldungen
```

#### **Wöchentlich prüfen:**
```
Performance-Indikatoren:
📊 Festplatte: ___% verwendet (< 80% = gut)
📊 Speicher: Läuft flüssig (subjektiv)
📊 Internet: ___Mbit gemessen (> 150 = gut)
📊 Uptime: __ Tage ohne Neustart
```

### **🔴 Remote-Support - Detaillierte Metriken:**

#### **System-Health-Dashboard:**
- **CPU-Load:** 1-Min, 5-Min, 15-Min Average
- **Memory-Usage:** Used/Available/Cached
- **Disk-Usage:** Root + Data Partitions
- **Network-I/O:** In/Out Traffic
- **Service-Status:** All critical services

#### **Application-Metrics:**
- **Response-Times:** Average/P95/P99
- **Error-Rates:** 4xx/5xx responses
- **User-Activity:** Active sessions
- **Database-Performance:** Query times
- **Cache-Hit-Rates:** Application caching

---

## 📝 **WARTUNGS-LOG-TEMPLATE**

### **Für Chef - Einfaches Excel/Word:**
```
Datum | Zeit | Status | Probleme | Maßnahmen | Bemerkungen
------|------|--------|----------|-----------|------------
01.12 | 09:00| ✅ OK  | Keine    | -         | Alles normal
02.12 | 09:15| ⚠️ Slow| Langsam  | Neustart  | Nach Neustart OK
03.12 | 08:45| ❌ Down| Nicht err| Luke anruf| Problem behoben
```

### **Für Remote-Support - Detailliert:**
```
Maintenance-Report Template:
=============================

Date: [YYYY-MM-DD]
Duration: [HH:MM]
Performed by: [Name]
Type: [Daily/Weekly/Monthly/Emergency]

System Status:
- Uptime: [Days]
- Load Average: [1m, 5m, 15m]
- Memory Usage: [%]
- Disk Usage: [%]
- Network: [OK/Issues]

Services Status:
- Nginx: [Running/Stopped/Issues]
- Flask App: [Running/Stopped/Issues]
- SSH: [Running/Stopped/Issues]
- Backup: [OK/Failed/Skipped]

Actions Performed:
- [ ] System updates
- [ ] Log review
- [ ] Performance optimization
- [ ] Security check
- [ ] Backup verification

Issues Found:
1. [Description]
   - Severity: [Low/Medium/High/Critical]
   - Resolution: [Description/Pending]

Next Actions:
- [ ] [Action item 1]
- [ ] [Action item 2]

Overall Assessment: [Good/Attention Needed/Critical]
```

---

**💡 Regelmäßige Wartung verhindert 90% aller Probleme! Bei Unsicherheiten lieber einmal zu oft nachfragen.**