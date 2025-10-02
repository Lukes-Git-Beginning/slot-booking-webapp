# Troubleshooting Guide
## Slot-Booking Server - Problemlösungen

---

## 🎯 **Übersicht**
Dieser Guide hilft bei der Lösung häufiger Probleme während und nach der Server-Installation. Strukturiert nach Installationsphasen und Problemkategorien.

**Zielgruppe:** Chef (Basis-Troubleshooting) + Remote-Support (Erweitert)
**Schwierigkeit:** Einfach bis Mittel

---

## 📋 **Problem-Kategorien**

### **1. Hardware & BIOS**
### **2. Ubuntu Installation**
### **3. Netzwerk & Fritzbox**
### **4. SSH & Remote-Zugang**
### **5. Server-Betrieb**
### **6. Performance-Probleme**

---

## 🖥️ **1. HARDWARE & BIOS PROBLEME**

### **❌ Problem: Server startet nicht**

#### **Symptom:**
- Schwarzer Bildschirm
- Kein BIOS-Bildschirm
- Lüfter laufen, aber kein Display

#### **Lösungsschritte:**
```bash
1. Hardware-Check:
   - Stromkabel fest angeschlossen?
   - Monitor-Kabel (VGA/HDMI) korrekt?
   - RAM-Module fest im Slot?

2. BIOS-Reset:
   - CMOS-Batterie 30 Sekunden entfernen
   - Oder BIOS-Reset-Jumper verwenden
   - Neustart versuchen

3. Minimalkonfiguration:
   - Nur 1 RAM-Modul
   - Nur SSD angeschlossen
   - USB-Geräte entfernen
```

#### **Chef kann selbst:**
✅ Kabel-Verbindungen prüfen
✅ RAM neu stecken
✅ Anderen Monitor versuchen

#### **Remote-Support nötig:**
❌ BIOS-Einstellungen ändern
❌ Hardware-Diagnose

---

### **❌ Problem: USB-Stick wird nicht erkannt**

#### **Symptom:**
- BIOS zeigt USB-Stick nicht an
- Boot-Menü listet USB nicht auf

#### **Lösungsschritte:**
```bash
1. USB-Stick prüfen:
   - Anderen USB-Port versuchen
   - USB-Stick an anderem PC testen
   - LED am Stick leuchtet?

2. BIOS-Einstellungen:
   - USB-Support aktiviert?
   - Legacy Boot aktiviert?
   - UEFI + Legacy-Modus

3. USB neu erstellen:
   - Rufus mit anderen Einstellungen
   - Anderen USB-Stick verwenden
   - ISO-Datei neu herunterladen
```

#### **Chef kann selbst:**
✅ USB-Port wechseln
✅ Anderen USB-Stick versuchen
✅ USB an anderem PC testen

---

### **❌ Problem: Tastatur funktioniert nicht**

#### **Symptom:**
- Tastatur reagiert nicht im BIOS
- Kann nicht navigieren

#### **Lösungsschritte:**
```bash
1. Tastatur-Check:
   - USB-Tastatur verwenden (nicht PS/2)
   - Anderen USB-Port versuchen
   - Caps-Lock LED reagiert?

2. BIOS-Einstellungen:
   - USB-Keyboard-Support aktivieren
   - Legacy USB-Support aktivieren

3. Alternative:
   - USB-Maus versuchen
   - Andere Tastatur testen
```

---

## 🐧 **2. UBUNTU INSTALLATION PROBLEME**

### **❌ Problem: Installation hängt fest**

#### **Symptom:**
- Installation stoppt bei bestimmtem Prozentsatz
- "Installing system..." ohne Fortschritt
- Bildschirm friert ein

#### **Lösungsschritte:**
```bash
1. Geduld haben:
   - Installation kann 30+ Minuten dauern
   - Bei HDD-Installation besonders langsam

2. Hardware-Check:
   - RAM-Test durchführen
   - Festplatten-SMART-Status prüfen
   - Überhitzung vermeiden

3. Neustart der Installation:
   - Server komplett herunterfahren
   - 30 Sekunden warten
   - Neustart mit USB-Stick
```

#### **Chef kann selbst:**
✅ 30 Minuten warten
✅ Server neu starten
✅ Installation wiederholen

#### **Remote-Support nötig:**
❌ Hardware-Diagnose
❌ Erweiterte Installations-Optionen

---

### **❌ Problem: Festplatten nicht erkannt**

#### **Symptom:**
- "No disks detected"
- SSD/HDD werden nicht angezeigt
- Storage-Konfiguration zeigt nichts

#### **Lösungsschritte:**
```bash
1. BIOS-Check:
   - SATA-Ports aktiviert?
   - AHCI-Modus aktiviert (nicht IDE)
   - RAID-Modus deaktiviert

2. Hardware-Check:
   - SATA-Kabel fest angeschlossen?
   - Stromkabel an Festplatten?
   - Festplatten-LED blinkt?

3. Live-System-Test:
   - Ubuntu Live-USB starten
   - Terminal öffnen: lsblk
   - Festplatten sichtbar?
```

---

### **❌ Problem: Netzwerk während Installation**

#### **Symptom:**
- "No internet connection"
- IP-Adresse 169.254.x.x (APIPA)
- Mirror-Download fehlschlägt

#### **Lösungsschritte:**
```bash
1. Hardware-Check:
   - Netzwerkkabel fest angeschlossen?
   - Link-LED am Port leuchtet?
   - Anderes Netzwerkkabel versuchen

2. Router-Check:
   - Ist Router online?
   - DHCP aktiviert?
   - Andere Geräte haben Internet?

3. Installation fortsetzen:
   - Ohne Internet installieren
   - Netzwerk später konfigurieren
```

#### **Chef kann selbst:**
✅ Kabel-Verbindung prüfen
✅ Router-Status prüfen
✅ Installation ohne Internet fortsetzen

---

## 🌐 **3. NETZWERK & FRITZBOX PROBLEME**

### **❌ Problem: Server bekommt keine IP-Adresse**

#### **Symptom:**
- `ip addr show` zeigt keine IP
- Ping zum Router fehlschlägt
- DHCP-Lease nicht erhalten

#### **Lösungsschritte:**
```bash
1. Netzwerk-Interface prüfen:
sudo ip link show
sudo ip link set enp0s25 up

2. DHCP-Client neu starten:
sudo dhclient -r
sudo dhclient

3. Network-Manager neu starten:
sudo systemctl restart systemd-networkd
sudo systemctl restart networking

4. Statische IP setzen (temporär):
sudo ip addr add 192.168.178.150/24 dev enp0s25
sudo ip route add default via 192.168.178.1
```

#### **Chef kann selbst:**
✅ Router neu starten
✅ Netzwerkkabel tauschen
✅ Anderen LAN-Port verwenden

#### **Remote-Support nötig:**
❌ Linux-Netzwerk-Konfiguration
❌ Erweiterte Netzwerk-Diagnose

---

### **❌ Problem: Fritzbox-Interface nicht erreichbar**

#### **Symptom:**
- `http://fritz.box` lädt nicht
- `http://192.168.178.1` timeout
- "Diese Website ist nicht erreichbar"

#### **Lösungsschritte:**
```bash
1. PC-Netzwerk prüfen:
   - WLAN/LAN-Verbindung aktiv?
   - Andere Webseiten erreichbar?
   - IP-Konfiguration korrekt?

2. Router-Status prüfen:
   - Router-LEDs normal?
   - Power-LED dauerhaft grün?
   - Internet-LED grün?

3. Alternative Zugriffswege:
   - FRITZ!App Fon auf Smartphone
   - Direkter LAN-Zugang zum Router
   - Router-Reset (Notfall)
```

#### **Chef kann selbst:**
✅ Router-LEDs prüfen
✅ Anderen Browser versuchen
✅ PC-Netzwerk prüfen

---

### **❌ Problem: Port-Freigabe funktioniert nicht**

#### **Symptom:**
- Externe Verbindung zu Server fehlschlägt
- Port-Scan zeigt Ports als "closed"
- SSH von außen nicht möglich

#### **Lösungsschritte:**
```bash
1. Fritzbox-Konfiguration prüfen:
   - Port-Freigaben korrekt eingetragen?
   - Richtige IP-Adresse (192.168.178.100)?
   - Freigaben aktiviert?

2. Server-Firewall prüfen:
sudo ufw status
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443

3. Service-Status prüfen:
sudo systemctl status ssh
sudo netstat -tlnp | grep :22

4. Externe IP testen:
curl ifconfig.me
nmap -p 22,80,443 [EXTERNE-IP]
```

#### **Chef kann selbst:**
✅ Fritzbox-Freigaben prüfen
✅ Router neu starten
✅ Server neu starten

#### **Remote-Support nötig:**
❌ Linux-Firewall-Konfiguration
❌ Service-Diagnose
❌ Port-Scanning

---

## 🔐 **4. SSH & REMOTE-ZUGANG PROBLEME**

### **❌ Problem: SSH-Verbindung verweigert**

#### **Symptom:**
- "Connection refused"
- "ssh: connect to host X.X.X.X port 22: Connection refused"
- PowerShell/Terminal zeigt Fehler

#### **Lösungsschritte:**
```bash
1. SSH-Service prüfen:
sudo systemctl status ssh
sudo systemctl start ssh
sudo systemctl enable ssh

2. SSH-Konfiguration prüfen:
sudo nano /etc/ssh/sshd_config
# Port 22
# PermitRootLogin no
# PasswordAuthentication yes

3. Firewall-Check:
sudo ufw status
sudo ufw allow ssh
sudo ufw reload

4. Lokaler Test:
ssh slotadmin@192.168.178.100  # Von lokalem Netzwerk
ssh slotadmin@localhost        # Vom Server selbst
```

---

### **❌ Problem: SSH-Authentifizierung fehlgeschlagen**

#### **Symptom:**
- "Permission denied (publickey,password)"
- "Access denied"
- Falsches Passwort-Verhalten

#### **Lösungsschritte:**
```bash
1. Benutzerdaten prüfen:
   - Username: slotadmin (nicht root!)
   - Passwort korrekt eingeben
   - Caps-Lock deaktiviert?

2. SSH-Konfiguration:
sudo nano /etc/ssh/sshd_config
PasswordAuthentication yes
PermitRootLogin no
sudo systemctl restart ssh

3. Benutzer-Check:
id slotadmin
sudo passwd slotadmin  # Passwort neu setzen
```

#### **Chef kann selbst:**
✅ Passwort neu eingeben
✅ Username prüfen (slotadmin)
✅ Lokaler Login am Server testen

---

### **❌ Problem: TeamViewer startet nicht**

#### **Symptom:**
- "TeamViewer Daemon not running"
- TeamViewer-ID wird nicht angezeigt
- Remote-Verbindung fehlschlägt

#### **Lösungsschritte:**
```bash
1. Service-Status prüfen:
sudo systemctl status teamviewerd
sudo systemctl start teamviewerd
sudo systemctl enable teamviewerd

2. Installation prüfen:
teamviewer --info
sudo dpkg -l | grep teamviewer

3. Neuinstallation:
sudo apt remove teamviewer
wget https://download.teamviewer.com/download/linux/teamviewer_amd64.deb
sudo dpkg -i teamviewer_amd64.deb
sudo apt install -f

4. Daemon-Modus aktivieren:
sudo teamviewer --daemon enable
teamviewer --info
```

---

## ⚙️ **5. SERVER-BETRIEB PROBLEME**

### **❌ Problem: Server reagiert langsam**

#### **Symptom:**
- SSH-Verbindung verzögert
- Befehle brauchen lange
- Hohe CPU-/RAM-Auslastung

#### **Diagnose-Befehle:**
```bash
# System-Auslastung prüfen:
top
htop
free -h
df -h

# CPU-Auslastung:
lscpu
cat /proc/loadavg

# RAM-Auslastung:
cat /proc/meminfo
ps aux --sort=-%mem | head

# Festplatten-I/O:
iotop
iostat -x 1
```

#### **Lösungsansätze:**
```bash
1. Speicher-intensive Prozesse beenden:
sudo kill [PID]
sudo pkill -f [PROCESS-NAME]

2. Cache leeren:
sudo sync
echo 3 | sudo tee /proc/sys/vm/drop_caches

3. Swap-Usage prüfen:
swapon -s
sudo swapoff -a && sudo swapon -a

4. Festplatten-Check:
sudo fsck /dev/sda1
sudo smartctl -a /dev/sda
```

#### **Chef kann selbst:**
✅ Server neu starten
✅ Weniger Programme gleichzeitig laufen lassen

#### **Remote-Support nötig:**
❌ Detaillierte Performance-Analyse
❌ System-Optimierung

---

### **❌ Problem: Festplatten-Speicher voll**

#### **Symptom:**
- "No space left on device"
- `df -h` zeigt 100% Usage
- Operationen fehlschlagen

#### **Lösungsschritte:**
```bash
1. Speicher-Analyse:
df -h
du -sh /*
du -sh /var/log/*
du -sh /tmp/*

2. Log-Dateien bereinigen:
sudo journalctl --vacuum-time=7d
sudo find /var/log -type f -name "*.log" -mtime +7 -delete
sudo apt autoremove
sudo apt autoclean

3. Temporäre Dateien löschen:
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

4. Package-Cache bereinigen:
sudo apt clean
sudo apt autoremove --purge
```

---

### **❌ Problem: Services starten nicht**

#### **Symptom:**
- Webserver nicht erreichbar
- SSH-Service fehlt
- "Failed to start" Meldungen

#### **Diagnose:**
```bash
# Service-Status prüfen:
sudo systemctl status nginx
sudo systemctl status ssh
sudo systemctl status teamviewerd

# Error-Logs anzeigen:
sudo journalctl -u nginx -f
sudo journalctl -u ssh -f

# Service-Liste:
sudo systemctl list-failed
```

#### **Lösungsansätze:**
```bash
1. Service neu starten:
sudo systemctl restart nginx
sudo systemctl restart ssh

2. Service aktivieren:
sudo systemctl enable nginx
sudo systemctl enable ssh

3. Konfiguration prüfen:
sudo nginx -t
sudo sshd -t

4. Ports prüfen:
sudo netstat -tlnp
sudo ss -tulpn
```

---

## 🚀 **6. PERFORMANCE-PROBLEME**

### **❌ Problem: Langsame Internet-Verbindung**

#### **Symptom:**
- Downloads sehr langsam
- Webseiten laden verzögert
- Unter 200 Mbit Performance

#### **Diagnose-Tools:**
```bash
# Speedtest (CLI):
sudo apt install speedtest-cli
speedtest-cli

# Ping-Test:
ping -c 10 google.de
ping -c 10 192.168.178.1

# DNS-Test:
nslookup google.de
dig google.de

# Bandwidth-Test:
iperf3 -c speedtest.tele2.net -p 5201
```

#### **Lösungsansätze:**
```bash
1. Netzwerk-Optimierung:
   - QoS in Fritzbox prüfen
   - Andere Geräte temporär trennen
   - LAN statt WLAN verwenden

2. DNS-Server ändern:
sudo nano /etc/systemd/resolved.conf
DNS=8.8.8.8 8.8.4.4
sudo systemctl restart systemd-resolved

3. MTU-Größe optimieren:
sudo ip link set enp0s25 mtu 1500
ping -M do -s 1472 google.de
```

#### **Chef kann selbst:**
✅ Router neu starten
✅ Speedtest an anderem Gerät
✅ QoS-Einstellungen in Fritzbox prüfen

---

### **❌ Problem: Hohe CPU-Auslastung**

#### **Symptom:**
- `top` zeigt >80% CPU-Usage
- System reagiert träge
- Lüfter laufen dauerhaft hoch

#### **Diagnose:**
```bash
# Top-Prozesse identifizieren:
top -o %CPU
ps aux --sort=-%cpu | head -20

# CPU-Info:
lscpu
cat /proc/cpuinfo

# Load-Average:
uptime
cat /proc/loadavg
```

#### **Lösungsansätze:**
```bash
1. Ressourcen-intensive Prozesse beenden:
sudo kill [HIGH-CPU-PID]
sudo pkill -f [PROCESS-NAME]

2. Nice-Werte anpassen:
sudo renice +10 [PID]

3. System-Services überprüfen:
sudo systemctl list-units --state=running
sudo systemctl disable [UNNECESSARY-SERVICE]

4. Cron-Jobs prüfen:
crontab -l
sudo crontab -l
```

---

## 🆘 **NOTFALL-PROZEDUREN**

### **🚨 Kompletter System-Ausfall**

#### **Symptom:**
- Server bootet nicht mehr
- Keine SSH-Verbindung möglich
- Schwarzer Bildschirm

#### **Notfall-Schritte:**
```bash
1. Hard-Reset:
   - Power-Button 10 Sekunden halten
   - 30 Sekunden warten
   - Neustart versuchen

2. Hardware-Reset:
   - Stromkabel 60 Sekunden ziehen
   - RAM-Module neu stecken
   - Minimalkonfiguration testen

3. Recovery-Boot:
   - Ubuntu Live-USB starten
   - Festplatten auf Fehler prüfen
   - Daten-Backup erstellen

4. Neuinstallation (letztes Mittel):
   - Daten-Backup von /data
   - Ubuntu neu installieren
   - Backup einspielen
```

#### **Chef sollte:**
✅ Sofort Luke kontaktieren
✅ Keine weiteren Änderungen vornehmen
✅ Hardware-Status dokumentieren

---

### **🚨 Sicherheits-Zwischenfall**

#### **Verdächtige Aktivitäten:**
- Unbekannte Prozesse
- Hoher Netzwerk-Traffic
- Fremde SSH-Connections

#### **Sofort-Maßnahmen:**
```bash
1. Netzwerk trennen:
   - Netzwerkkabel ziehen
   - Oder: sudo ip link set enp0s25 down

2. Verdächtige Prozesse prüfen:
ps aux | grep -v "\[.*\]"
sudo netstat -tlnp
sudo ss -tulpn

3. SSH-Logs prüfen:
sudo tail -100 /var/log/auth.log
sudo tail -100 /var/log/syslog

4. Sofort-Kontakt:
   - Luke informieren
   - Keine weiteren Änderungen
   - System offline lassen
```

---

## 📞 **SUPPORT-KONTAKTE**

### **Basis-Support (Chef kann selbst):**
- Hardware-Checks
- Router-Neustart
- Server-Neustart
- Kabel-Verbindungen

### **Remote-Support nötig:**
- Linux-Konfiguration
- Service-Diagnose
- Performance-Optimierung
- Sicherheits-Analysen

### **Notfall-Kontakte:**
- **Luke:** [Telefonnummer] (24/7 bei kritischen Problemen)
- **TeamViewer:** Für direkte Remote-Hilfe
- **SSH-Zugang:** Bei Netzwerk-Problemen

---

## 📋 **CHECKLISTEN**

### **Tägliche Checks:**
- [ ] Server läuft und ist erreichbar
- [ ] SSH-Verbindung funktioniert
- [ ] Webservice antwortet
- [ ] Festplatten-Speicher ausreichend

### **Wöchentliche Checks:**
- [ ] System-Updates installieren
- [ ] Log-Dateien prüfen
- [ ] Backup-Status verifizieren
- [ ] Performance-Monitoring

### **Monatliche Checks:**
- [ ] Fritzbox-Firmware aktualisieren
- [ ] Sicherheits-Patches installieren
- [ ] Festplatten-Health prüfen
- [ ] Netzwerk-Performance testen

---

**💡 Bei Problemen: Erst this Guide konsultieren, dann Remote-Support kontaktieren!**