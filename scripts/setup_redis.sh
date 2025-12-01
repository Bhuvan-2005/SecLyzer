#!/bin/bash
# Redis Setup Script for SecLyzer

set -e

echo "=== SecLyzer Redis Setup ==="

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "Redis is not installed. Installing..."
    sudo apt update
    sudo apt install -y redis-server redis-tools
else
    echo "✓ Redis is already installed"
fi

# Check if Redis is running
if ! systemctl is-active --quiet redis-server; then
    echo "Starting Redis server..."
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
else
    echo "✓ Redis is already running"
fi

# Configure Redis for SecLyzer
echo "Configuring Redis..."
REDIS_CONF="/etc/redis/redis.conf"

# Backup original config
if [ ! -f "${REDIS_CONF}.backup" ]; then
    sudo cp $REDIS_CONF ${REDIS_CONF}.backup
    echo "✓ Backed up original Redis config"
fi

# Set max memory (256 MB as per optimization plan)
sudo sed -i 's/^# maxmemory <bytes>/maxmemory 256mb/' $REDIS_CONF
sudo sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' $REDIS_CONF

# Bind to localhost only (security)
sudo sed -i 's/^bind 127.0.0.1 ::1/bind 127.0.0.1/' $REDIS_CONF

# Restart Redis to apply changes
sudo systemctl restart redis-server

echo "✓ Redis configured with:"
echo "  - Max memory: 256 MB"
echo "  - Eviction policy: allkeys-lru"
echo "  - Bind address: 127.0.0.1 (localhost only)"

# Test connection
if redis-cli ping | grep -q "PONG"; then
    echo "✓ Redis is responsive"
else
    echo "✗ Redis test failed"
    exit 1
fi

echo ""
echo "=== Redis Setup Complete ==="
echo "You can monitor Redis with: redis-cli monitor"
