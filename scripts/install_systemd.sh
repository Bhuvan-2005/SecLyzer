#!/bin/bash
# Install SecLyzer systemd services for auto-start
# Run as: sudo ./install_systemd.sh <username>

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

if [ -z "$1" ]; then
    echo "Usage: sudo $0 <username>"
    echo "Example: sudo $0 bhuvan"
    exit 1
fi

USERNAME=$1
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing SecLyzer systemd services for user: $USERNAME"
echo "Project root: $PROJECT_ROOT"
echo ""

# Create log directory
mkdir -p /var/log/seclyzer
chown $USERNAME:$USERNAME /var/log/seclyzer

# Copy service files
echo "Installing service files..."
cp "$PROJECT_ROOT/systemd/seclyzer-keyboard@.service" /etc/systemd/system/
cp "$PROJECT_ROOT/systemd/seclyzer-mouse@.service" /etc/systemd/system/
cp "$PROJECT_ROOT/systemd/seclyzer-app@.service" /etc/systemd/system/
cp "$PROJECT_ROOT/systemd/seclyzer-extractors@.service" /etc/systemd/system/

echo "✓ Service files installed"

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable services
echo "Enabling services for user $USERNAME..."
systemctl enable seclyzer-keyboard@$USERNAME
systemctl enable seclyzer-mouse@$USERNAME
systemctl enable seclyzer-app@$USERNAME
systemctl enable seclyzer-extractors@$USERNAME

echo "✓ Services enabled"
echo ""
echo "To start services now:"
echo "  sudo systemctl start seclyzer-keyboard@$USERNAME"
echo "  sudo systemctl start seclyzer-mouse@$USERNAME"
echo "  sudo systemctl start seclyzer-app@$USERNAME"
echo "  sudo systemctl start seclyzer-extractors@$USERNAME"
echo ""
echo "To check status:"
echo "  systemctl status seclyzer-*@$USERNAME"
echo ""
echo "Services will auto-start on boot."
