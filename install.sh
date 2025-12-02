#!/bin/bash
# ============================================================================
# SecLyzer Automated Installation Script
# Fully automated installation with sensible defaults
# ============================================================================
#
# Usage:
#   ./install.sh                    # Interactive mode (default)
#   ./install.sh --auto             # Fully automated with defaults
#   ./install.sh --auto --no-redis  # Automated without Redis installation
#   ./install.sh --help             # Show help
#
# Environment variables for customization:
#   SECLYZER_INSTALL_DIR    - Installation directory (default: /opt/seclyzer)
#   SECLYZER_DATA_DIR       - Data directory (default: /var/lib/seclyzer)
#   SECLYZER_LOG_DIR        - Log directory (default: /var/log/seclyzer)
#   SECLYZER_CONFIG_DIR     - Config directory (default: /etc/seclyzer)
#   SECLYZER_VENV_PATH      - Python venv path (default: auto-detected)
#   SECLYZER_PASSWORD       - Admin password (default: auto-generated)
#
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_INSTALL_DIR="/opt/seclyzer"
DEFAULT_DATA_DIR="/var/lib/seclyzer"
DEFAULT_LOG_DIR="/var/log/seclyzer"
DEFAULT_CONFIG_DIR="/etc/seclyzer"
DEFAULT_REDIS_MEMORY="256mb"

# Parse command line arguments
AUTO_MODE=false
INSTALL_REDIS=true
INSTALL_INFLUXDB=true
ENABLE_AUTOSTART=true
SKIP_BUILD=false
SHOW_HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto|-a)
            AUTO_MODE=true
            shift
            ;;
        --no-redis)
            INSTALL_REDIS=false
            shift
            ;;
        --no-influxdb)
            INSTALL_INFLUXDB=false
            shift
            ;;
        --no-autostart)
            ENABLE_AUTOSTART=false
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Show help
if [ "$SHOW_HELP" = true ]; then
    echo "SecLyzer Installation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --auto, -a        Fully automated installation with defaults"
    echo "  --no-redis        Skip Redis installation"
    echo "  --no-influxdb     Skip InfluxDB installation"
    echo "  --no-autostart    Don't enable systemd auto-start"
    echo "  --skip-build      Skip building Rust collectors"
    echo "  --help, -h        Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  SECLYZER_INSTALL_DIR    Installation directory"
    echo "  SECLYZER_DATA_DIR       Data directory"
    echo "  SECLYZER_LOG_DIR        Log directory"
    echo "  SECLYZER_CONFIG_DIR     Config directory"
    echo "  SECLYZER_VENV_PATH      Python virtual environment path"
    echo "  SECLYZER_PASSWORD       Admin password"
    echo ""
    exit 0
fi

# Banner
show_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║           SecLyzer Installation Script                    ║"
    echo "║     Behavioral Biometric Authentication System            ║"
    echo "║                                                           ║"
    echo "║                    Version 0.3.1                          ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}✗ Please run as root (use sudo)${NC}"
        exit 1
    fi
}

# Get actual user (not root)
get_actual_user() {
    ACTUAL_USER=${SUDO_USER:-$USER}
    ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)
    echo -e "${GREEN}✓${NC} Installing for user: $ACTUAL_USER"
}

# Set configuration from environment or defaults
set_configuration() {
    INSTALL_DIR="${SECLYZER_INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
    DATA_DIR="${SECLYZER_DATA_DIR:-$DEFAULT_DATA_DIR}"
    LOG_DIR="${SECLYZER_LOG_DIR:-$DEFAULT_LOG_DIR}"
    CONFIG_DIR="${SECLYZER_CONFIG_DIR:-$DEFAULT_CONFIG_DIR}"
    REDIS_MEMORY="${SECLYZER_REDIS_MEMORY:-$DEFAULT_REDIS_MEMORY}"
    
    # Auto-detect or use provided venv path
    if [ -n "$SECLYZER_VENV_PATH" ]; then
        VENV_PATH="$SECLYZER_VENV_PATH"
    elif [ -d "$ACTUAL_HOME/Documents/Projects/venv" ]; then
        VENV_PATH="$ACTUAL_HOME/Documents/Projects/venv"
    elif [ -d "$ACTUAL_HOME/.venv" ]; then
        VENV_PATH="$ACTUAL_HOME/.venv"
    elif [ -d "$ACTUAL_HOME/venv" ]; then
        VENV_PATH="$ACTUAL_HOME/venv"
    else
        VENV_PATH="$ACTUAL_HOME/.seclyzer-venv"
    fi
    
    # Generate or use provided password
    if [ -n "$SECLYZER_PASSWORD" ]; then
        PASSWORD="$SECLYZER_PASSWORD"
    else
        PASSWORD=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 16)
    fi
    PASSWORD_HASH=$(echo -n "$PASSWORD" | sha256sum | cut -d' ' -f1)
}

# Interactive configuration
interactive_config() {
    echo -e "${CYAN}=== Installation Configuration ===${NC}"
    echo ""
    
    read -p "Install directory [$INSTALL_DIR]: " input
    INSTALL_DIR=${input:-$INSTALL_DIR}
    
    read -p "Data directory [$DATA_DIR]: " input
    DATA_DIR=${input:-$DATA_DIR}
    
    read -p "Log directory [$LOG_DIR]: " input
    LOG_DIR=${input:-$LOG_DIR}
    
    read -p "Config directory [$CONFIG_DIR]: " input
    CONFIG_DIR=${input:-$CONFIG_DIR}
    
    read -p "Python venv path [$VENV_PATH]: " input
    VENV_PATH=${input:-$VENV_PATH}
    
    read -p "Install Redis? [Y/n]: " input
    [[ "$input" =~ ^[Nn]$ ]] && INSTALL_REDIS=false
    
    read -p "Install InfluxDB? [Y/n]: " input
    [[ "$input" =~ ^[Nn]$ ]] && INSTALL_INFLUXDB=false
    
    read -p "Enable auto-start? [Y/n]: " input
    [[ "$input" =~ ^[Nn]$ ]] && ENABLE_AUTOSTART=false
    
    echo ""
    echo "Set admin password for SecLyzer:"
    while true; do
        read -s -p "Password: " PASSWORD
        echo ""
        read -s -p "Confirm: " PASSWORD_CONFIRM
        echo ""
        if [ "$PASSWORD" = "$PASSWORD_CONFIRM" ] && [ ${#PASSWORD} -ge 6 ]; then
            PASSWORD_HASH=$(echo -n "$PASSWORD" | sha256sum | cut -d' ' -f1)
            break
        fi
        echo -e "${RED}Passwords don't match or too short (min 6 chars)${NC}"
    done
}

# Show configuration summary
show_config() {
    echo ""
    echo -e "${CYAN}=== Configuration Summary ===${NC}"
    echo "  Install Dir:    $INSTALL_DIR"
    echo "  Data Dir:       $DATA_DIR"
    echo "  Log Dir:        $LOG_DIR"
    echo "  Config Dir:     $CONFIG_DIR"
    echo "  Python Venv:    $VENV_PATH"
    echo "  Install Redis:  $INSTALL_REDIS"
    echo "  Install InfluxDB: $INSTALL_INFLUXDB"
    echo "  Auto-start:     $ENABLE_AUTOSTART"
    echo ""
}

# Create directories
create_directories() {
    echo "Creating directories..."
    mkdir -p "$INSTALL_DIR"/{bin,lib,scripts}
    mkdir -p "$DATA_DIR"/{databases,models,datasets}
    mkdir -p "$LOG_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Set ownership
    chown -R "$ACTUAL_USER:$ACTUAL_USER" "$DATA_DIR"
    chown -R "$ACTUAL_USER:$ACTUAL_USER" "$LOG_DIR"
    
    # Create .gitkeep files
    touch "$DATA_DIR/datasets/.gitkeep"
    touch "$DATA_DIR/models/.gitkeep"
    
    echo -e "${GREEN}✓${NC} Directories created"
}

# Install system dependencies
install_dependencies() {
    echo ""
    echo "Installing system dependencies..."
    
    apt-get update -qq
    
    DEPS="build-essential pkg-config libx11-dev libxext-dev libxtst-dev \
          python3 python3-pip python3-venv python3-dev \
          sqlite3 curl git bc"
    
    apt-get install -y $DEPS > /dev/null 2>&1
    
    echo -e "${GREEN}✓${NC} System dependencies installed"
}

# Install Redis
install_redis() {
    if [ "$INSTALL_REDIS" = false ]; then
        echo -e "${YELLOW}⚠${NC} Skipping Redis installation"
        return
    fi
    
    echo ""
    echo "Installing Redis..."
    
    if ! command -v redis-server &> /dev/null; then
        apt-get install -y redis-server redis-tools > /dev/null 2>&1
    fi
    
    # Configure Redis
    REDIS_CONF="/etc/redis/redis.conf"
    if [ -f "$REDIS_CONF" ]; then
        # Backup
        cp "$REDIS_CONF" "${REDIS_CONF}.bak.$(date +%s)" 2>/dev/null || true
        
        # Configure
        sed -i "s/^# maxmemory .*/maxmemory $REDIS_MEMORY/" "$REDIS_CONF"
        sed -i "s/^maxmemory .*/maxmemory $REDIS_MEMORY/" "$REDIS_CONF"
        sed -i "s/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/" "$REDIS_CONF"
        sed -i "s/^maxmemory-policy .*/maxmemory-policy allkeys-lru/" "$REDIS_CONF"
        sed -i "s/^bind .*/bind 127.0.0.1/" "$REDIS_CONF"
    fi
    
    systemctl enable redis-server > /dev/null 2>&1
    systemctl restart redis-server
    
    echo -e "${GREEN}✓${NC} Redis installed and configured"
}

# Install InfluxDB
install_influxdb() {
    if [ "$INSTALL_INFLUXDB" = false ]; then
        echo -e "${YELLOW}⚠${NC} Skipping InfluxDB installation"
        return
    fi
    
    echo ""
    echo "Installing InfluxDB..."
    
    if ! command -v influx &> /dev/null; then
        # Add repository
        curl -s https://repos.influxdata.com/influxdata-archive_compat.key | \
            gpg --dearmor > /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg 2>/dev/null
        
        echo "deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main" | \
            tee /etc/apt/sources.list.d/influxdata.list > /dev/null
        
        apt-get update -qq
        apt-get install -y influxdb2 > /dev/null 2>&1
    fi
    
    systemctl enable influxdb > /dev/null 2>&1
    systemctl start influxdb
    
    # Wait for InfluxDB
    for i in {1..30}; do
        curl -s http://localhost:8086/ping > /dev/null 2>&1 && break
        sleep 1
    done
    
    # Initialize if not already done
    if ! influx auth list &> /dev/null 2>&1; then
        INFLUX_PASSWORD=$(openssl rand -base64 16)
        
        influx setup \
            --org "seclyzer" \
            --bucket "behavioral_data" \
            --username "seclyzer_admin" \
            --password "$INFLUX_PASSWORD" \
            --retention "30d" \
            --force > /dev/null 2>&1 || true
        
        # Create and save token
        TEMP_FILE="/tmp/influx_token_$$.json"
        influx auth create --org "seclyzer" --read-buckets --write-buckets --json > "$TEMP_FILE" 2>/dev/null || true
        
        if [ -f "$TEMP_FILE" ]; then
            INFLUX_TOKEN=$(grep -o '"token": *"[^"]*"' "$TEMP_FILE" 2>/dev/null | cut -d'"' -f4)
            rm -f "$TEMP_FILE"
            
            if [ -n "$INFLUX_TOKEN" ]; then
                echo "$INFLUX_TOKEN" > "$CONFIG_DIR/influxdb_token"
                chmod 600 "$CONFIG_DIR/influxdb_token"
            fi
        fi
        
        # Save credentials
        echo "INFLUX_PASSWORD=$INFLUX_PASSWORD" >> "$CONFIG_DIR/.credentials"
        chmod 600 "$CONFIG_DIR/.credentials"
    fi
    
    echo -e "${GREEN}✓${NC} InfluxDB installed and configured"
}

# Install Rust
install_rust() {
    echo ""
    echo "Checking Rust installation..."
    
    if ! sudo -u "$ACTUAL_USER" bash -c 'command -v cargo' &> /dev/null; then
        echo "Installing Rust..."
        sudo -u "$ACTUAL_USER" bash -c 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y' > /dev/null 2>&1
        echo -e "${GREEN}✓${NC} Rust installed"
    else
        echo -e "${GREEN}✓${NC} Rust already installed"
    fi
}

# Build collectors
build_collectors() {
    if [ "$SKIP_BUILD" = true ]; then
        echo -e "${YELLOW}⚠${NC} Skipping collector build"
        return
    fi
    
    echo ""
    echo "Building Rust collectors (this may take 2-5 minutes)..."
    
    sudo -u "$ACTUAL_USER" bash -c "
        source '$ACTUAL_HOME/.cargo/env' 2>/dev/null || true
        cd '$SCRIPT_DIR/collectors/keyboard_collector' && cargo build --release 2>/dev/null
        cd '$SCRIPT_DIR/collectors/mouse_collector' && cargo build --release 2>/dev/null
        cd '$SCRIPT_DIR/collectors/app_monitor' && cargo build --release 2>/dev/null
    "
    
    # Copy binaries
    cp "$SCRIPT_DIR/collectors/keyboard_collector/target/release/keyboard_collector" "$INSTALL_DIR/bin/" 2>/dev/null || true
    cp "$SCRIPT_DIR/collectors/mouse_collector/target/release/mouse_collector" "$INSTALL_DIR/bin/" 2>/dev/null || true
    cp "$SCRIPT_DIR/collectors/app_monitor/target/release/app_monitor" "$INSTALL_DIR/bin/" 2>/dev/null || true
    
    chmod +x "$INSTALL_DIR/bin/"* 2>/dev/null || true
    
    echo -e "${GREEN}✓${NC} Collectors built"
}

# Setup Python environment
setup_python() {
    echo ""
    echo "Setting up Python environment..."
    
    # Create venv if needed
    if [ ! -d "$VENV_PATH" ]; then
        sudo -u "$ACTUAL_USER" python3 -m venv "$VENV_PATH"
    fi
    
    # Install dependencies
    sudo -u "$ACTUAL_USER" bash -c "
        source '$VENV_PATH/bin/activate'
        pip install -q --upgrade pip
        pip install -q redis polars influxdb-client scikit-learn numpy pydantic onnxruntime joblib
    " 2>/dev/null
    
    echo -e "${GREEN}✓${NC} Python environment ready"
}

# Setup SQLite database
setup_sqlite() {
    echo ""
    echo "Setting up SQLite database..."
    
    DB_FILE="$DATA_DIR/databases/seclyzer.db"
    
    sqlite3 "$DB_FILE" << 'EOF'
CREATE TABLE IF NOT EXISTS user_profile (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    training_status TEXT DEFAULT 'initial',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS models (
    model_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    model_type TEXT NOT NULL,
    version TEXT,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accuracy REAL,
    model_path TEXT,
    is_active INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES user_profile(user_id)
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    confidence_score REAL,
    state TEXT,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_models_user ON models(user_id);

INSERT OR IGNORE INTO user_profile (username, training_status) VALUES ('default', 'initial');
INSERT OR IGNORE INTO config (key, value) VALUES ('version', '0.3.1');
INSERT OR IGNORE INTO config (key, value) VALUES ('installed_at', datetime('now'));
EOF
    
    chown "$ACTUAL_USER:$ACTUAL_USER" "$DB_FILE"
    chmod 600 "$DB_FILE"
    
    echo -e "${GREEN}✓${NC} SQLite database ready"
}

# Copy project files
copy_files() {
    echo ""
    echo "Copying project files..."
    
    # Copy Python modules
    cp -r "$SCRIPT_DIR/common" "$INSTALL_DIR/lib/"
    cp -r "$SCRIPT_DIR/storage" "$INSTALL_DIR/lib/"
    cp -r "$SCRIPT_DIR/processing" "$INSTALL_DIR/lib/"
    cp -r "$SCRIPT_DIR/daemon" "$INSTALL_DIR/lib/"
    
    # Copy scripts
    cp "$SCRIPT_DIR/scripts/seclyzer" "$INSTALL_DIR/bin/"
    cp "$SCRIPT_DIR/scripts/dev" "$INSTALL_DIR/bin/seclyzer-dev"
    cp "$SCRIPT_DIR/scripts/start_collectors.sh" "$INSTALL_DIR/scripts/"
    cp "$SCRIPT_DIR/scripts/start_extractors.sh" "$INSTALL_DIR/scripts/"
    cp "$SCRIPT_DIR/scripts/stop_extractors.sh" "$INSTALL_DIR/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts/train_models.py" "$INSTALL_DIR/scripts/"
    
    chmod +x "$INSTALL_DIR/bin/"*
    chmod +x "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true
    
    # Copy config
    cp "$SCRIPT_DIR/config/seclyzer.yml" "$CONFIG_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR/.env.example" "$CONFIG_DIR/.env" 2>/dev/null || true
    
    # Update paths in config
    if [ -f "$CONFIG_DIR/seclyzer.yml" ]; then
        sed -i "s|data/databases|$DATA_DIR/databases|g" "$CONFIG_DIR/seclyzer.yml"
        sed -i "s|data/models|$DATA_DIR/models|g" "$CONFIG_DIR/seclyzer.yml"
        sed -i "s|data/logs|$LOG_DIR|g" "$CONFIG_DIR/seclyzer.yml"
    fi
    
    echo -e "${GREEN}✓${NC} Files copied"
}

# Create systemd services
create_systemd_services() {
    echo ""
    echo "Creating systemd services..."
    
    # Keyboard collector
    cat > /etc/systemd/system/seclyzer-keyboard.service << EOF
[Unit]
Description=SecLyzer Keyboard Collector
After=network.target redis-server.service

[Service]
Type=simple
User=root
Environment="DISPLAY=:0"
ExecStart=$INSTALL_DIR/bin/keyboard_collector
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Mouse collector
    cat > /etc/systemd/system/seclyzer-mouse.service << EOF
[Unit]
Description=SecLyzer Mouse Collector
After=network.target redis-server.service

[Service]
Type=simple
User=root
Environment="DISPLAY=:0"
ExecStart=$INSTALL_DIR/bin/mouse_collector
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # App monitor
    cat > /etc/systemd/system/seclyzer-app.service << EOF
[Unit]
Description=SecLyzer App Monitor
After=network.target redis-server.service

[Service]
Type=simple
User=$ACTUAL_USER
Environment="DISPLAY=:0"
ExecStart=$INSTALL_DIR/bin/app_monitor
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Feature extractors
    cat > /etc/systemd/system/seclyzer-extractors.service << EOF
[Unit]
Description=SecLyzer Feature Extractors
After=network.target redis-server.service seclyzer-keyboard.service

[Service]
Type=forking
User=$ACTUAL_USER
Environment="PYTHONPATH=$INSTALL_DIR/lib"
Environment="VENV_PATH=$VENV_PATH"
ExecStart=/bin/bash -c 'source $VENV_PATH/bin/activate && cd $INSTALL_DIR/lib && python3 processing/extractors/keystroke_extractor.py & python3 processing/extractors/mouse_extractor.py & python3 processing/extractors/app_tracker.py &'
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    
    if [ "$ENABLE_AUTOSTART" = true ]; then
        systemctl enable seclyzer-keyboard.service > /dev/null 2>&1
        systemctl enable seclyzer-mouse.service > /dev/null 2>&1
        systemctl enable seclyzer-app.service > /dev/null 2>&1
        echo -e "${GREEN}✓${NC} Systemd services created and enabled"
    else
        echo -e "${GREEN}✓${NC} Systemd services created (not enabled)"
    fi
}

# Save installation metadata
save_metadata() {
    echo ""
    echo "Saving installation metadata..."
    
    cat > "$INSTALL_DIR/.install_metadata" << EOF
INSTALL_DIR=$INSTALL_DIR
DATA_DIR=$DATA_DIR
LOG_DIR=$LOG_DIR
CONFIG_DIR=$CONFIG_DIR
VENV_PATH=$VENV_PATH
ACTUAL_USER=$ACTUAL_USER
INSTALL_DATE=$(date -Iseconds)
VERSION=0.3.1
REDIS_INSTALLED=$INSTALL_REDIS
INFLUXDB_INSTALLED=$INSTALL_INFLUXDB
AUTOSTART_ENABLED=$ENABLE_AUTOSTART
EOF
    
    # Save password hash
    echo "$PASSWORD_HASH" > "$CONFIG_DIR/.password_hash"
    chmod 600 "$CONFIG_DIR/.password_hash"
    
    echo -e "${GREEN}✓${NC} Metadata saved"
}

# Create symlinks
create_symlinks() {
    echo ""
    echo "Creating symlinks..."
    
    ln -sf "$INSTALL_DIR/bin/seclyzer" /usr/local/bin/seclyzer 2>/dev/null || true
    ln -sf "$INSTALL_DIR/bin/seclyzer-dev" /usr/local/bin/seclyzer-dev 2>/dev/null || true
    
    echo -e "${GREEN}✓${NC} Symlinks created"
}

# Create uninstall script
create_uninstaller() {
    cat > "$INSTALL_DIR/uninstall.sh" << 'UNINSTALL_EOF'
#!/bin/bash
# ============================================================================
# SecLyzer Uninstallation Script
# Auto-generated during installation
# ============================================================================
#
# Usage:
#   ./uninstall.sh                  # Interactive mode
#   ./uninstall.sh --auto           # Fully automated (keeps data)
#   ./uninstall.sh --auto --purge   # Fully automated (removes everything)
#   ./uninstall.sh --help           # Show help
#
# Environment variables:
#   SECLYZER_PASSWORD    - Admin password for verification
#
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load installation metadata
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
METADATA_FILE="$SCRIPT_DIR/.install_metadata"

if [ ! -f "$METADATA_FILE" ]; then
    echo -e "${RED}✗ Installation metadata not found${NC}"
    echo "Cannot proceed with uninstallation."
    exit 1
fi

source "$METADATA_FILE"

# Parse arguments
AUTO_MODE=false
PURGE_MODE=false
SHOW_HELP=false
SKIP_PASSWORD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto|-a)
            AUTO_MODE=true
            shift
            ;;
        --purge|-p)
            PURGE_MODE=true
            shift
            ;;
        --skip-password)
            SKIP_PASSWORD=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Show help
if [ "$SHOW_HELP" = true ]; then
    echo "SecLyzer Uninstallation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --auto, -a        Fully automated uninstallation (keeps data by default)"
    echo "  --purge, -p       Remove all data including models and logs"
    echo "  --skip-password   Skip password verification (use with caution)"
    echo "  --help, -h        Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  SECLYZER_PASSWORD    Admin password for verification"
    echo ""
    echo "Examples:"
    echo "  sudo ./uninstall.sh                    # Interactive"
    echo "  sudo ./uninstall.sh --auto             # Auto, keep data"
    echo "  sudo ./uninstall.sh --auto --purge     # Auto, remove everything"
    echo "  sudo SECLYZER_PASSWORD=xxx ./uninstall.sh --auto"
    echo ""
    exit 0
fi

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           SecLyzer Uninstallation Script                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# Show what will be removed
echo "Installation found:"
echo "  Install Dir:  $INSTALL_DIR"
echo "  Data Dir:     $DATA_DIR"
echo "  Config Dir:   $CONFIG_DIR"
echo "  Log Dir:      $LOG_DIR"
echo ""

# Password verification
verify_password() {
    if [ "$SKIP_PASSWORD" = true ]; then
        return 0
    fi
    
    local password_file="$CONFIG_DIR/.password_hash"
    
    if [ ! -f "$password_file" ]; then
        return 0  # No password set
    fi
    
    local stored_hash=$(cat "$password_file")
    local entered_password=""
    local entered_hash=""
    
    # Check environment variable first
    if [ -n "$SECLYZER_PASSWORD" ]; then
        entered_hash=$(echo -n "$SECLYZER_PASSWORD" | sha256sum | cut -d' ' -f1)
        if [ "$entered_hash" = "$stored_hash" ]; then
            echo -e "${GREEN}✓${NC} Password verified (from environment)"
            return 0
        else
            echo -e "${RED}✗ Incorrect password in SECLYZER_PASSWORD${NC}"
            return 1
        fi
    fi
    
    # Interactive password prompt
    if [ "$AUTO_MODE" = true ]; then
        echo -e "${RED}✗ Password required. Set SECLYZER_PASSWORD or use --skip-password${NC}"
        return 1
    fi
    
    read -s -p "Enter SecLyzer password: " entered_password
    echo ""
    
    entered_hash=$(echo -n "$entered_password" | sha256sum | cut -d' ' -f1)
    
    if [ "$entered_hash" = "$stored_hash" ]; then
        echo -e "${GREEN}✓${NC} Password verified"
        return 0
    else
        echo -e "${RED}✗ Incorrect password${NC}"
        return 1
    fi
}

# Verify password
if ! verify_password; then
    echo "Uninstallation cancelled."
    exit 1
fi

# Confirmation (interactive mode only)
if [ "$AUTO_MODE" = false ]; then
    echo -e "${YELLOW}This will remove SecLyzer from your system.${NC}"
    echo ""
    read -p "Continue with uninstallation? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Uninstallation cancelled."
        exit 0
    fi
    echo ""
fi

echo "Starting uninstallation..."
echo ""

# Stop all running processes
echo "Stopping SecLyzer processes..."
pkill -f "seclyzer_daemon.py" 2>/dev/null || true
pkill -f "keystroke_extractor.py" 2>/dev/null || true
pkill -f "mouse_extractor.py" 2>/dev/null || true
pkill -f "app_tracker.py" 2>/dev/null || true
pkill -f "keyboard_collector" 2>/dev/null || true
pkill -f "mouse_collector" 2>/dev/null || true
pkill -f "app_monitor" 2>/dev/null || true
echo -e "${GREEN}✓${NC} Processes stopped"

# Stop and disable systemd services
echo "Removing systemd services..."
systemctl stop seclyzer-keyboard.service 2>/dev/null || true
systemctl stop seclyzer-mouse.service 2>/dev/null || true
systemctl stop seclyzer-app.service 2>/dev/null || true
systemctl stop seclyzer-extractors.service 2>/dev/null || true

systemctl disable seclyzer-keyboard.service 2>/dev/null || true
systemctl disable seclyzer-mouse.service 2>/dev/null || true
systemctl disable seclyzer-app.service 2>/dev/null || true
systemctl disable seclyzer-extractors.service 2>/dev/null || true

rm -f /etc/systemd/system/seclyzer-*.service
systemctl daemon-reload
echo -e "${GREEN}✓${NC} Systemd services removed"

# Remove symlinks
echo "Removing symlinks..."
rm -f /usr/local/bin/seclyzer 2>/dev/null || true
rm -f /usr/local/bin/seclyzer-dev 2>/dev/null || true
echo -e "${GREEN}✓${NC} Symlinks removed"

# Remove configuration
echo "Removing configuration..."
rm -rf "$CONFIG_DIR"
echo -e "${GREEN}✓${NC} Configuration removed"

# Handle data directory
REMOVE_DATA=false
if [ "$PURGE_MODE" = true ]; then
    REMOVE_DATA=true
elif [ "$AUTO_MODE" = false ]; then
    echo ""
    read -p "Remove data directory ($DATA_DIR)? This includes trained models! [y/N]: " r
    [[ "$r" =~ ^[Yy]$ ]] && REMOVE_DATA=true
fi

if [ "$REMOVE_DATA" = true ]; then
    echo "Removing data directory..."
    rm -rf "$DATA_DIR"
    echo -e "${GREEN}✓${NC} Data removed"
else
    echo -e "${YELLOW}⚠${NC} Data directory preserved: $DATA_DIR"
fi

# Handle log directory
REMOVE_LOGS=false
if [ "$PURGE_MODE" = true ]; then
    REMOVE_LOGS=true
elif [ "$AUTO_MODE" = false ]; then
    read -p "Remove log directory ($LOG_DIR)? [y/N]: " r
    [[ "$r" =~ ^[Yy]$ ]] && REMOVE_LOGS=true
fi

if [ "$REMOVE_LOGS" = true ]; then
    echo "Removing log directory..."
    rm -rf "$LOG_DIR"
    echo -e "${GREEN}✓${NC} Logs removed"
else
    echo -e "${YELLOW}⚠${NC} Log directory preserved: $LOG_DIR"
fi

# Remove installation directory (do this last since we're running from it)
echo "Removing installation directory..."
# Copy this script to temp and continue from there
TEMP_CLEANUP="/tmp/seclyzer_cleanup_$$.sh"
cat > "$TEMP_CLEANUP" << CLEANUP_EOF
#!/bin/bash
sleep 1
rm -rf "$INSTALL_DIR"
rm -f "$TEMP_CLEANUP"
CLEANUP_EOF
chmod +x "$TEMP_CLEANUP"
nohup "$TEMP_CLEANUP" > /dev/null 2>&1 &

echo -e "${GREEN}✓${NC} Installation directory will be removed"

# Final message
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       SecLyzer Uninstallation Complete!                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$REMOVE_DATA" = false ]; then
    echo -e "${YELLOW}Note: Your data is preserved at: $DATA_DIR${NC}"
    echo "To remove it manually: sudo rm -rf $DATA_DIR"
    echo ""
fi

if [ "$REMOVE_LOGS" = false ]; then
    echo -e "${YELLOW}Note: Your logs are preserved at: $LOG_DIR${NC}"
    echo "To remove them manually: sudo rm -rf $LOG_DIR"
    echo ""
fi

echo "Thank you for using SecLyzer!"
UNINSTALL_EOF
    chmod +x "$INSTALL_DIR/uninstall.sh"
    echo -e "${GREEN}✓${NC} Uninstall script created"
}

# Show completion message
show_completion() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║       SecLyzer Installation Complete!                     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Installation Summary:"
    echo "  ✓ Install Dir:  $INSTALL_DIR"
    echo "  ✓ Data Dir:     $DATA_DIR"
    echo "  ✓ Config Dir:   $CONFIG_DIR"
    echo "  ✓ Log Dir:      $LOG_DIR"
    echo ""
    
    if [ -z "$SECLYZER_PASSWORD" ]; then
        echo -e "${YELLOW}Generated Admin Password: $PASSWORD${NC}"
        echo -e "${YELLOW}(Save this password - you'll need it to manage SecLyzer)${NC}"
        echo ""
    fi
    
    echo "Quick Start:"
    echo "  1. Start services:    sudo systemctl start seclyzer-keyboard seclyzer-mouse seclyzer-app"
    echo "  2. Check status:      seclyzer status"
    echo "  3. View logs:         seclyzer logs"
    echo ""
    echo "Or use the control script:"
    echo "  seclyzer start        # Start all collectors"
    echo "  seclyzer extractors   # Start feature extractors"
    echo "  seclyzer status       # Check status"
    echo ""
    echo "For development:"
    echo "  seclyzer-dev help     # Show all developer commands"
    echo ""
    echo "To uninstall:"
    echo "  sudo $INSTALL_DIR/uninstall.sh              # Interactive"
    echo "  sudo $INSTALL_DIR/uninstall.sh --auto       # Automated (keeps data)"
    echo "  sudo $INSTALL_DIR/uninstall.sh --auto --purge  # Remove everything"
    echo ""
}

# ============================================================================
# Main Installation Flow
# ============================================================================

main() {
    show_banner
    check_root
    get_actual_user
    set_configuration
    
    if [ "$AUTO_MODE" = false ]; then
        interactive_config
    fi
    
    show_config
    
    if [ "$AUTO_MODE" = false ]; then
        read -p "Proceed with installation? [Y/n]: " confirm
        [[ "$confirm" =~ ^[Nn]$ ]] && exit 0
    fi
    
    echo ""
    echo -e "${BLUE}Starting installation...${NC}"
    
    create_directories
    install_dependencies
    install_redis
    install_influxdb
    install_rust
    build_collectors
    setup_python
    setup_sqlite
    copy_files
    create_systemd_services
    save_metadata
    create_symlinks
    create_uninstaller
    
    show_completion
}

# Run main
main
