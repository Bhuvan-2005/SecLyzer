#!/bin/bash
# InfluxDB Setup Script for SecLyzer

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║      SecLyzer InfluxDB Setup                      ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# Configuration
INFLUX_ORG="seclyzer"
INFLUX_BUCKET="behavioral_data"
INFLUX_RETENTION="30d"  # 30 days retention
INFLUX_USER="seclyzer_admin"
INFLUX_PASSWORD=$(openssl rand -base64 32)  # Random password
INFLUX_TOKEN_FILE="/etc/seclyzer/influxdb_token"

echo "Checking for InfluxDB..."

if command -v influx &> /dev/null; then
    echo -e "${GREEN}✓${NC} InfluxDB already installed"
else
    echo "Installing InfluxDB..."
    
    # Add InfluxDB repository
    curl -s https://repos.influxdata.com/influxdata-archive_compat.key | gpg --dearmor > /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg
    
    echo "deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main" | tee /etc/apt/sources.list.d/influxdata.list
    
    apt update -qq
    apt install -y influxdb2
    
    echo -e "${GREEN}✓${NC} InfluxDB installed"
fi

# Start InfluxDB service
echo ""
echo "Starting InfluxDB service..."
systemctl enable influxdb
systemctl start influxdb

# Wait for InfluxDB to be ready
echo "Waiting for InfluxDB to start..."
for i in {1..30}; do
    if curl -s http://localhost:8086/ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} InfluxDB is running"
        break
    fi
    sleep 1
done

# Check if already initialized
if influx auth list &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} InfluxDB already initialized"
    read -p "Recreate organization and bucket? [y/N]: " recreate
    if [[ ! "$recreate" =~ ^[Yy]$ ]]; then
        echo "Skipping initialization."
        exit 0
    fi
fi

# Initialize InfluxDB
echo ""
echo "Initializing InfluxDB..."

influx setup \
    --org "$INFLUX_ORG" \
    --bucket "$INFLUX_BUCKET" \
    --username "$INFLUX_USER" \
    --password "$INFLUX_PASSWORD" \
    --retention "$INFLUX_RETENTION" \
    --force

echo -e "${GREEN}✓${NC} InfluxDB initialized"

# Create API token
echo ""
echo "Creating API token..."

# Use temp file to capture output reliably
TEMP_TOKEN_JSON="/tmp/influx_token_create.json"
influx auth create \
    --org "$INFLUX_ORG" \
    --read-buckets \
    --write-buckets \
    --json > "$TEMP_TOKEN_JSON"

# Extract token using grep/cut (more robust than piping directly)
TOKEN=$(grep -o '"token": *"[^"]*"' "$TEMP_TOKEN_JSON" | cut -d'"' -f4)
rm -f "$TEMP_TOKEN_JSON"

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Failed to create API token${NC}"
    exit 1
fi

# Save token to file
mkdir -p /etc/seclyzer
echo "$TOKEN" > "$INFLUX_TOKEN_FILE"
chmod 600 "$INFLUX_TOKEN_FILE"

echo -e "${GREEN}✓${NC} API token created and saved to $INFLUX_TOKEN_FILE"

# Update SecLyzer config
CONFIG_FILE="/etc/seclyzer/seclyzer.yml"
if [ -f "$CONFIG_FILE" ]; then
    echo ""
    echo "Updating SecLyzer configuration..."
    
    # Use sed to update the token in YAML
    sed -i "s/token: .*/token: \"$TOKEN\"/" "$CONFIG_FILE"
    sed -i "s/org: .*/org: \"$INFLUX_ORG\"/" "$CONFIG_FILE"
    sed -i "s/bucket: .*/bucket: \"$INFLUX_BUCKET\"/" "$CONFIG_FILE"
    
    echo -e "${GREEN}✓${NC} Configuration updated"
fi

# Configure retention policy
echo ""
echo "Setting up retention policy..."

influx bucket update \
    --name "$INFLUX_BUCKET" \
    --retention "$INFLUX_RETENTION" \
    --org "$INFLUX_ORG" > /dev/null 2>&1 || true

echo -e "${GREEN}✓${NC} Retention policy set to $INFLUX_RETENTION"

# Performance tuning
echo ""
echo "Optimizing InfluxDB settings..."

INFLUX_CONFIG="/etc/influxdb/config.toml"
if [ -f "$INFLUX_CONFIG" ]; then
    # Backup original config
    cp "$INFLUX_CONFIG" "${INFLUX_CONFIG}.backup_$(date +%Y%m%d_%H%M%S)"
    
    # Set cache size (for better performance)
    cat >> "$INFLUX_CONFIG" << EOF

# SecLyzer optimizations
[storage-cache]
  max-concurrent-compactions = 2
  cache-max-memory-size = "512MB"
  cache-snapshot-memory-size = "25MB"
EOF

    systemctl restart influxdb
    echo -e "${GREEN}✓${NC} Performance tuning applied"
fi

# Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   InfluxDB Setup Complete!                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

echo "Configuration:"
echo "  Organization: $INFLUX_ORG"
echo "  Bucket: $INFLUX_BUCKET"
echo "  Retention: $INFLUX_RETENTION"
echo "  URL: http://localhost:8086"
echo "  Token: Saved to $INFLUX_TOKEN_FILE"
echo ""

echo "Credentials (SAVE THESE!):"
echo "  Username: $INFLUX_USER"
echo "  Password: $INFLUX_PASSWORD"
echo ""

echo -e "${YELLOW}⚠ IMPORTANT: Save the password above! You'll need it to access InfluxDB UI${NC}"
echo ""

echo "Next steps:"
echo "  1. Access UI: http://localhost:8086"
echo "  2. Login with username/password above"
echo "  3. Run: sudo ./scripts/setup_sqlite.sh"
echo ""
