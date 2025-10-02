# Ubuntu Server 22.04 LTS Installation Guide
## Für Slot-Booking Server beim Chef

---

## 🎯 **Übersicht**
Diese Anleitung führt Schritt-für-Schritt durch die Installation von Ubuntu Server 22.04 LTS auf dem Chef-Server (i5-3470, 12GB RAM, 4TB HDD + 128GB SSD).

**Zeitaufwand:** 45-60 Minuten
**Schwierigkeit:** Einfach (GUI-geführt)
**Benötigt:** USB-Stick (8GB+), Monitor, Tastatur

---

## 📋 **Vorbereitung**

### **1. Hardware prüfen**
- [ ] Server ist ausgeschaltet
- [ ] Monitor und Tastatur angeschlossen
- [ ] Netzwerkkabel vom Router zum Server
- [ ] USB-Stick (mindestens 8GB) bereit

### **2. Ubuntu ISO herunterladen**
1. **Website besuchen:** https://ubuntu.com/download/server
2. **Version wählen:** Ubuntu Server 22.04.3 LTS
3. **Datei:** `ubuntu-22.04.3-live-server-amd64.iso` (ca. 1.4GB)
4. **Download-Zeit:** ~10 Minuten bei 200 Mbit

### **3. Bootfähigen USB-Stick erstellen**
1. **Rufus herunterladen:** https://rufus.ie/
2. **Rufus starten** (als Administrator)
3. **Einstellungen:**
   - Laufwerk: USB-Stick auswählen
   - Abbild: Ubuntu ISO-Datei wählen
   - Partitionsschema: GPT
   - Zielsystem: UEFI
4. **"START" klicken** und warten (5-10 Minuten)

⚠️ **WICHTIG:** Alle Daten auf USB-Stick werden gelöscht!

---

## 🖥️ **BIOS/UEFI Konfiguration**

### **1. Server starten und BIOS öffnen**
1. **USB-Stick einstecken**
2. **Server einschalten**
3. **Sofort F2 oder DEL drücken** (mehrmals)
4. **BIOS-Menü sollte erscheinen**

### **2. Boot-Reihenfolge ändern**
```
Boot Menu → Boot Priority:
1. USB-HDD (Ubuntu-Stick)
2. SATA HDD/SSD
3. Network Boot
```

### **3. Secure Boot (falls vorhanden)**
- **Secure Boot:** Disabled
- **Fast Boot:** Disabled
- **Legacy Support:** Enabled

### **4. Speichern und Neustart**
- **F10 drücken** → "Save and Exit"
- **Yes** bestätigen
- **Server startet neu**

---

## 🐧 **Ubuntu Installation**

### **1. Boot-Bildschirm**
```
GNU GRUB Menü erscheint:
→ "Try or Install Ubuntu Server" wählen
→ ENTER drücken
```

### **2. Sprache auswählen**
```
Language Selection:
→ "English" wählen (empfohlen für Server)
→ ENTER
```

### **3. Installer-Update**
```
Installer update available:
→ "Continue without updating" wählen
→ ENTER
```

### **4. Tastaturlayout**
```
Keyboard configuration:
Layout: [English (US)]
Variant: [English (US)]

→ "Done" wählen
→ ENTER
```

### **5. Installationstyp**
```
Choose type of install:
→ "Ubuntu Server" (bereits ausgewählt)
→ "Done"
```

### **6. Netzwerk-Konfiguration**
```
Network connections:
enp0s25: DHCPv4 192.168.178.XXX/24

→ Automatische IP-Konfiguration ist OK
→ "Done"
```

⚠️ **IP-Adresse notieren!** Wird später für SSH benötigt.

### **7. Proxy-Konfiguration**
```
Configure proxy:
Proxy address: [leer lassen]

→ "Done"
```

### **8. Mirror-Konfiguration**
```
Configure Ubuntu archive mirror:
Mirror: http://de.archive.ubuntu.com/ubuntu

→ Standard-Mirror ist OK
→ "Done"
```

---

## 💾 **Festplatten-Konfiguration (KRITISCH!)**

### **1. Storage-Übersicht**
```
Guided storage configuration:
□ Use an entire disk
☑ Custom storage layout

→ "Custom storage layout" ANKREUZEN!
→ "Done"
```

### **2. Festplatten-Layout erstellen**

#### **SSD (128GB) - System-Partition:**
```
Available devices:
/dev/sda  128G  Samsung SSD

→ /dev/sda auswählen
→ "Add GPT Partition"

Partition 1:
Size: 100G
Format: ext4
Mount: /

Partition 2:
Size: 20G
Format: swap
Mount: [swap]
```

#### **HDD (4TB) - Daten-Partition:**
```
Available devices:
/dev/sdb  4T  Seagate HDD

→ /dev/sdb auswählen
→ "Add GPT Partition"

Partition 1:
Size: 4T (maximum)
Format: ext4
Mount: /data
```

### **3. Layout bestätigen**
```
Final storage layout:
/dev/sda1  100G  ext4  /
/dev/sda2   20G  swap  [swap]
/dev/sdb1    4T  ext4  /data

→ "Done"
```

⚠️ **WARNUNG:** "Confirm destructive action" → **"Continue"**

---

## 👤 **Benutzer-Konfiguration**

### **1. Profil-Setup**
```
Profile setup:
Your name: Slot Admin
Your server's name: slot-server
Pick a username: slotadmin
Choose a password: [STARKES PASSWORT!]
Confirm your password: [WIEDERHOLEN]

→ "Done"
```

**⚠️ PASSWORT-ANFORDERUNGEN:**
- Mindestens 12 Zeichen
- Groß-/Kleinbuchstaben + Zahlen + Sonderzeichen
- **SICHER AUFBEWAHREN!**

### **2. SSH-Setup**
```
SSH Setup:
☑ Install OpenSSH server

Import SSH identity: No

→ "Done"
```

**✅ OpenSSH MUSS aktiviert sein für Remote-Zugang!**

### **3. Featured Server Snaps**
```
Featured Server Snaps:
□ docker
□ microk8s
□ ...

→ NICHTS auswählen (alles leer lassen)
→ "Done"
```

---

## ⏳ **Installation durchführen**

### **1. Installations-Prozess**
```
Installing system...

Progress:
[████████████████████████████████] 100%

Dauer: 15-25 Minuten
```

### **2. Installation abgeschlossen**
```
Installation complete!
□ Reboot Now

→ "Reboot Now" ANKREUZEN
→ "Done"
```

### **3. USB-Stick entfernen**
```
Please remove the installation medium, then press ENTER:

→ USB-Stick herausziehen
→ ENTER drücken
```

---

## ✅ **Erster Start und Test**

### **1. Login-Bildschirm**
```
slot-server login: slotadmin
Password: [PASSWORT EINGEBEN]

slotadmin@slot-server:~$
```

### **2. System-Info prüfen**
```bash
# System-Version
lsb_release -a

# Festplatten-Layout prüfen
df -h

# Netzwerk-Info
ip addr show

# Internet-Test
ping -c 3 google.de
```

### **3. IP-Adresse notieren**
```bash
ip addr show | grep "inet.*eth0"
# Ausgabe: inet 192.168.178.XXX/24

→ Diese IP für SSH verwenden!
```

---

## 🔧 **Erste Updates**

### **1. System aktualisieren**
```bash
sudo apt update
sudo apt upgrade -y
```

### **2. Zusätzliche Tools installieren**
```bash
sudo apt install -y htop curl wget nano ufw
```

### **3. Firewall aktivieren**
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw status
```

---

## 📞 **SSH-Test vom Windows-PC**

### **1. PowerShell öffnen**
- **Windows-Taste + R**
- **"powershell" eingeben**
- **ENTER**

### **2. SSH-Verbindung testen**
```powershell
ssh slotadmin@192.168.178.XXX

# Beim ersten Mal:
The authenticity of host ... can't be established.
Are you sure you want to continue connecting (yes/no)? yes

Password: [PASSWORT EINGEBEN]
```

### **3. Erfolgreicher SSH-Login**
```bash
Welcome to Ubuntu 22.04.3 LTS
slotadmin@slot-server:~$

# Test-Befehl:
whoami
# Ausgabe: slotadmin
```

---

## ✅ **Installation erfolgreich!**

### **Checkliste vor Remote-Session:**
- [ ] Ubuntu Server läuft und ist erreichbar
- [ ] SSH-Zugang funktioniert
- [ ] Internet-Verbindung funktioniert
- [ ] IP-Adresse notiert: `192.168.178.XXX`
- [ ] Login-Daten sicher aufbewahrt

### **Nächste Schritte:**
1. **Fritzbox konfigurieren** (siehe nächster Guide)
2. **TeamViewer installieren** für Remote-Support
3. **Remote-Session** für Server-Konfiguration

---

## 🆘 **Häufige Probleme**

### **Problem: Server bootet nicht von USB**
**Lösung:**
- BIOS-Boot-Reihenfolge prüfen
- USB-Stick in anderen Port stecken
- Secure Boot deaktivieren

### **Problem: Tastatur funktioniert nicht**
**Lösung:**
- USB-Tastatur verwenden (nicht PS/2)
- Anderen USB-Port versuchen
- Im BIOS USB-Support aktivieren

### **Problem: Kein Internet**
**Lösung:**
- Netzwerkkabel prüfen
- Router-Status prüfen
- `sudo dhclient` ausführen

### **Problem: SSH-Verbindung fehlschlägt**
**Lösung:**
- IP-Adresse korrekt? `ip addr show`
- Firewall: `sudo ufw allow ssh`
- SSH-Service: `sudo systemctl status ssh`

---

## 📞 **Support-Kontakte**

**Bei Problemen während Installation:**
- **Luke:** [Telefonnummer]
- **Alternative:** TeamViewer nach Ubuntu-Installation

**Nach erfolgreicher Installation:**
- **SSH-Remote-Zugang** für weitere Konfiguration
- **Fritzbox-Konfiguration** (nächster Guide)

---

**🎉 Herzlichen Glückwunsch! Ubuntu Server ist erfolgreich installiert!**