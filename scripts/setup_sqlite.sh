#!/bin/bash
# SQLite Setup Script for SecLyzer

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║      SecLyzer SQLite Setup                        ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Configuration
DB_DIR="/var/lib/seclyzer/databases"
DB_FILE="$DB_DIR/seclyzer.db"
SCHEMA_FILE="$(dirname "$0")/../storage/schemas/sqlite_schema.sql"

# Create directory
echo "Creating database directory..."
mkdir -p "$DB_DIR"

# Create empty database
echo "Creating SQLite database..."
touch "$DB_FILE"

# Apply schema
echo "Applying schema..."
if [ -f "$SCHEMA_FILE" ]; then
    sqlite3 "$DB_FILE" < "$SCHEMA_FILE"
    echo -e "${GREEN}✓${NC} Schema applied"
else
    echo "Schema file not found, creating manually..."
    
    # Create schema inline
    sqlite3 "$DB_FILE" << 'EOF'
-- User profile
CREATE TABLE IF NOT EXISTS user_profile (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    training_status TEXT DEFAULT 'initial',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Model metadata
CREATE TABLE IF NOT EXISTS models (
    model_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    model_type TEXT NOT NULL,
    version TEXT,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accuracy REAL,
    model_path TEXT,
    FOREIGN KEY(user_id) REFERENCES user_profile(user_id)
);

-- Configuration
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    confidence_score REAL,
    state TEXT,
    details TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_models_user ON models(user_id);
CREATE INDEX IF NOT EXISTS idx_models_type ON models(model_type);

-- Insert default user
INSERT OR IGNORE INTO user_profile (username, training_status) 
VALUES ('default', 'initial');

-- Insert default config
INSERT OR IGNORE INTO config (key, value) VALUES ('version', '1.0.0');
INSERT OR IGNORE INTO config (key, value) VALUES ('installation_date', datetime('now'));
EOF

    echo -e "${GREEN}✓${NC} Schema created"
fi

# Set permissions
chown -R "$SUDO_USER:$SUDO_USER" "$DB_DIR"
chmod 600 "$DB_FILE"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   SQLite Setup Complete!                          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

echo "Database location: $DB_FILE"
echo "Tables created:"
echo "  - user_profile"
echo "  - models"
echo "  - config"
echo "  - audit_log"
echo ""

# Test database
echo "Testing database..."
TABLES=$(sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table';")
echo "Found tables:"
echo "$TABLES"

echo ""
echo -e "${GREEN}✓${NC} SQLite is ready!"
