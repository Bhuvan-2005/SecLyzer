#!/bin/bash
# SecLyzer System Backup Script
# Creates a snapshot of current models, database, and config

set -e

BACKUP_DIR="/var/lib/seclyzer/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_DIR="$BACKUP_DIR/snapshot_$TIMESTAMP"

echo "Creating system snapshot at $SNAPSHOT_DIR..."

mkdir -p "$SNAPSHOT_DIR"

# Backup Database
if [ -f "/var/lib/seclyzer/databases/seclyzer.db" ]; then
    cp "/var/lib/seclyzer/databases/seclyzer.db" "$SNAPSHOT_DIR/"
    echo "✓ Database backed up"
fi

# Backup Models
if [ -d "/var/lib/seclyzer/models" ]; then
    cp -r "/var/lib/seclyzer/models" "$SNAPSHOT_DIR/"
    echo "✓ Models backed up"
fi

# Backup Config
if [ -d "/etc/seclyzer" ]; then
    cp -r "/etc/seclyzer" "$SNAPSHOT_DIR/"
    echo "✓ Config backed up"
fi

echo "Snapshot complete. To restore:"
echo "sudo cp -r $SNAPSHOT_DIR/seclyzer.db /var/lib/seclyzer/databases/"
echo "sudo cp -r $SNAPSHOT_DIR/models/* /var/lib/seclyzer/models/"
echo "sudo cp -r $SNAPSHOT_DIR/seclyzer/* /etc/seclyzer/"
