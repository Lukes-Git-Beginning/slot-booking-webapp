#!/bin/bash

# ========================================
# SSH Key Setup für VPS
# ========================================
# Lädt den Public Key auf den VPS hoch
#
# VERWENDUNG:
#   bash setup_ssh_key.sh
#
# VORAUSSETZUNG:
#   Root-Passwort für VPS
# ========================================

VPS_IP="91.98.192.233"
VPS_USER="root"
SSH_KEY="./vps_key"

echo "========================================="
echo "  SSH Key Setup für VPS"
echo "========================================="
echo ""
echo "Public Key wird auf VPS hochgeladen: $VPS_USER@$VPS_IP"
echo ""

# Prüfen ob Key existiert
if [ ! -f "$SSH_KEY.pub" ]; then
    echo "❌ ERROR: SSH Public Key nicht gefunden!"
    echo "   Erwartet: $SSH_KEY.pub"
    exit 1
fi

echo "📤 Lade Public Key hoch..."
echo "   (Du wirst nach dem Root-Passwort gefragt)"
echo ""

# Public Key auf VPS hochladen und zu authorized_keys hinzufügen
ssh-copy-id -i "$SSH_KEY.pub" "$VPS_USER@$VPS_IP"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "  ✅ SSH Key erfolgreich installiert!"
    echo "========================================="
    echo ""
    echo "Du kannst jetzt ohne Passwort verbinden:"
    echo "  ssh -i $SSH_KEY $VPS_USER@$VPS_IP"
    echo ""
    echo "Nächster Schritt:"
    echo "  bash upload_t2_updates.sh"
    echo ""
else
    echo ""
    echo "❌ Fehler beim Hochladen des SSH Keys"
    echo "   Bitte prüfe Passwort und VPS-Verbindung"
    exit 1
fi
