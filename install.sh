#!/bin/bash
# SecLyzer Installation Script
# Interactive installer with user-configurable options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_INSTALL_DIR="/opt/seclyzer"
DEFAULT_DATA_DIR="/var/lib/seclyzer"
DEFAULT_LOG_DIR="/var/log/seclyzer"
DEFAULT_CONFIG_DIR="/etc/seclyzer"
DEFAULT_REDIS_MEMORY="256mb"

# User-selected values (will be set during prompts)
INSTALL_DIR=""
DATA_DIR=""
LOG_DIR=""
CONFIG_DIR=""
REDIS_MEMORY=""
INSTALL_REDIS=true
ENABLE_AUTOSTART=true
PYTHON_VENV_PATH="/home/$USER/Documents/Projects/venv"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║                                                   ║"
echo "║         SecLyzer Installation Wizard             ║"
echo "║    Behavioral Biometric Authentication System    ║"
echo "║                                                   ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo "This installer will set up SecLyzer on your system."
echo "You will be prompted to customize installation paths and options."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
echo -e "${GREEN}✓${NC} Installing for user: $ACTUAL_USER"
echo ""

# ===== Installation Path Configuration =====
echo -e "${YELLOW}=== Installation Paths ===${NC}"
echo ""

echo "Where should SecLyzer binaries be installed?"
read -p "Install directory [$DEFAULT_INSTALL_DIR]: " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}

echo "Where should data (models, databases) be stored?"
read -p "Data directory [$DEFAULT_DATA_DIR]: " DATA_DIR
DATA_DIR=${DATA_DIR:-$DEFAULT_DATA_DIR}

echo "Where should logs be stored?"
read -p "Log directory [$DEFAULT_LOG_DIR]: " LOG_DIR
LOG_DIR=${LOG_DIR:-$DEFAULT_LOG_DIR}

echo "Where should configuration files be stored?"
read -p "Config directory [$DEFAULT_CONFIG_DIR]: " CONFIG_DIR
CONFIG_DIR=${CONFIG_DIR:-$DEFAULT_CONFIG_DIR}

echo ""
echo -e "${GREEN}✓${NC} Installation paths configured:"
echo "  Binaries: $INSTALL_DIR"
echo "  Data: $DATA_DIR"
echo "  Logs: $LOG_DIR"
echo "  Config: $CONFIG_DIR"
echo ""

# ===== Redis Configuration =====
echo -e "${YELLOW}=== Redis Configuration ===${NC}"
echo ""

read -p "Install and configure Redis? [Y/n]: " install_redis_response
if [[ "$install_redis_response" =~ ^[Nn]$ ]]; then
    INSTALL_REDIS=false
    echo "⚠ Skipping Redis installation (you'll need to configure it manually)"
else
    echo "Redis memory limit (e.g., 256mb, 512mb, 1gb)?"
    read -p "Memory limit [$DEFAULT_REDIS_MEMORY]: " REDIS_MEMORY
    REDIS_MEMORY=${REDIS_MEMORY:-$DEFAULT_REDIS_MEMORY}
    echo -e "${GREEN}✓${NC} Redis will be installed with ${REDIS_MEMORY} memory limit"
fi

echo ""

# ===== Python Virtual Environment =====
echo -e "${YELLOW}=== Python Environment ===${NC}"
echo ""

echo "SecLyzer requires Python packages for ML and data processing."
read -p "Python virtual environment path [$PYTHON_VENV_PATH]: " user_venv
PYTHON_VENV_PATH=${user_venv:-$PYTHON_VENV_PATH}

if [ ! -d "$PYTHON_VENV_PATH" ]; then
    echo -e "${YELLOW}⚠${NC} Virtual environment not found at $PYTHON_VENV_PATH"
    read -p "Create it now? [Y/n]: " create_venv
    if [[ ! "$create_venv" =~ ^[Nn]$ ]]; then
        mkdir -p "$(dirname "$PYTHON_VENV_PATH")"
        python3 -m venv "$PYTHON_VENV_PATH"
        echo -e "${GREEN}✓${NC} Created virtual environment"
    fi
fi

echo ""

# ===== Auto-start Configuration =====
echo -e "${YELLOW}=== System Integration ===${NC}"
echo ""

read -p "Enable auto-start on boot (systemd service)? [Y/n]: " autostart_response
if [[ "$autostart_response" =~ ^[Nn]$ ]]; then
    ENABLE_AUTOSTART=false
    echo "⚠ Auto-start disabled (you'll need to run collectors manually)"
else
    echo -e "${GREEN}✓${NC} Auto-start will be enabled"
fi

echo ""

# ===== SecLyzer Password Setup =====
echo -e "${YELLOW}=== Security Password ===${NC}"
echo ""
echo "Set a password to protect SecLyzer control operations."
echo "This will be required for:"
echo "  - Disabling authentication"
echo "  - Stopping services"
echo "  - Uninstalling SecLyzer"
echo ""

SECLYZER_PASSWORD=""
while true; do
    read -s -p "Enter SecLyzer password: " SECLYZER_PASSWORD
    echo ""
    read -s -p "Confirm password: " SECLYZER_PASSWORD_CONFIRM
    echo ""
    
    if [ "$SECLYZER_PASSWORD" == "$SECLYZER_PASSWORD_CONFIRM" ]; then
        if [ ${#SECLYZER_PASSWORD} -lt 6 ]; then
            echo -e "${RED}✗ Password must be at least 6 characters${NC}"
            continue
        fi
        echo -e "${GREEN}✓${NC} Password set"
        break
    else
        echo -e "${RED}✗ Passwords do not match, try again${NC}"
    fi
done

# Hash the password
SECLYZER_PASSWORD_HASH=$(echo -n "$SECLYZER_PASSWORD" | sha256sum | cut -d' ' -f1)

echo ""

# ===== Confirmation =====
echo -e "${YELLOW}=== Installation Summary ===${NC}"
echo ""
echo "Installation Directory: $INSTALL_DIR"
echo "Data Directory: $DATA_DIR"
echo "Log Directory: $LOG_DIR"
echo "Config Directory: $CONFIG_DIR"
echo "Redis Installation: $INSTALL_REDIS"
if [ "$INSTALL_REDIS" = true ]; then
    echo "  Memory Limit: $REDIS_MEMORY"
fi
echo "Python Venv: $PYTHON_VENV_PATH"
echo "Auto-start: $ENABLE_AUTOSTART"
echo ""

read -p "Proceed with installation? [Y/n]: " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}Starting installation...${NC}"
echo ""

# ===== Create Directories =====
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"/{bin,config,scripts,collectors,common,storage,processing,training,docs}
mkdir -p "$DATA_DIR"/{databases,models,datasets/public}
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"
chown -R "$ACTUAL_USER":"$ACTUAL_USER" "$DATA_DIR"
chown -R "$ACTUAL_USER":"$ACTUAL_USER" "$LOG_DIR"
echo -e "${GREEN}✓${NC} Directories created"

# ===== Install System Dependencies =====
echo ""
echo "Installing system dependencies..."
apt update -qq
apt install -y \
    build-essential \
    pkg-config \
    libx11-dev \
    libxext-dev \
    libxtst-dev \
    python3 \
    python3-pip \
    python3-venv \
    sqlite3 \
    curl \
    git

echo -e "${GREEN}✓${NC} System dependencies installed"

# ===== Install Redis =====
if [ "$INSTALL_REDIS" = true ]; then
    echo ""
    echo "Installing Redis..."
    
    if ! command -v redis-server &> /dev/null; then
        apt install -y redis-server redis-tools
    fi
    
    # Configure Redis
    REDIS_CONF="/etc/redis/redis.conf"
    if [ -f "$REDIS_CONF" ]; then
        cp "$REDIS_CONF" "${REDIS_CONF}.backup_$(date +%Y%m%d_%H%M%S)"
        
        # Set memory limit
        sed -i "s/^# maxmemory .*/maxmemory $REDIS_MEMORY/" "$REDIS_CONF"
        sed -i "s/^maxmemory .*/maxmemory $REDIS_MEMORY/" "$REDIS_CONF"
        
        # Set eviction policy
        sed -i "s/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/" "$REDIS_CONF"
        sed -i "s/^maxmemory-policy .*/maxmemory-policy allkeys-lru/" "$REDIS_CONF"
        
        # Bind to localhost only
        sed -i "s/^bind .*/bind 127.0.0.1/" "$REDIS_CONF"
    fi
    
    systemctl enable redis-server
    systemctl restart redis-server
    
    echo -e "${GREEN}✓${NC} Redis installed and configured"
fi

# ===== Install Rust (if needed) =====
echo ""
echo "Checking Rust installation..."
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    sudo -u "$ACTUAL_USER" bash -c 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y'
    source /home/"$ACTUAL_USER"/.cargo/env
    echo -e "${GREEN}✓${NC} Rust installed"
else
    echo -e "${GREEN}✓${NC} Rust already installed"
fi

# Set PROJECT_ROOT and SOURCE_DIR
cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"
SOURCE_DIR="$PROJECT_ROOT"

# ===== Build Collectors =====
echo ""
echo "Building SecLyzer collectors (this may take 2-5 minutes)..."

# Build as the actual user (not root)
sudo -u "$ACTUAL_USER" bash -c "
    source /home/$ACTUAL_USER/.cargo/env
    cd '$PROJECT_ROOT/collectors/keyboard_collector' && cargo build --release
    cd '$PROJECT_ROOT/collectors/mouse_collector' && cargo build --release
    cd '$PROJECT_ROOT/collectors/app_monitor' && cargo build --release
"

# Copy binaries
cp collectors/keyboard_collector/target/release/keyboard_collector "$INSTALL_DIR/bin/"
cp collectors/mouse_collector/target/release/mouse_collector "$INSTALL_DIR/bin/"
cp collectors/app_monitor/target/release/app_monitor "$INSTALL_DIR/bin/"

# Set ownership
chown root:root "$INSTALL_DIR/bin/keyboard_collector"
chown root:root "$INSTALL_DIR/bin/mouse_collector"
chmod +x "$INSTALL_DIR/bin/"*

echo -e "${GREEN}✓${NC} Collectors built and installed"

# ===== Install Python Dependencies =====
echo ""
echo "Installing Python dependencies..."

sudo -u "$ACTUAL_USER" bash -c "
    source '$PYTHON_VENV_PATH/bin/activate'
    pip install -q --upgrade pip
    pip install -q redis polars influxdb-client scikit-learn
"

echo -e "${GREEN}✓${NC} Python dependencies installed"

# ===== Copy Configuration =====
echo ""
echo "Setting up configuration..."

# Update config file with user-selected paths
CONFIG_FILE="$CONFIG_DIR/seclyzer.yml"
cp "$PROJECT_ROOT/config/seclyzer.yml" "$CONFIG_FILE"

# Replace paths in config using sed
sed -i "s|data/databases/seclyzer.db|$DATA_DIR/databases/seclyzer.db|g" "$CONFIG_FILE"
sed -i "s|data/models/|$DATA_DIR/models/|g" "$CONFIG_FILE"
sed -i "s|data/logs/seclyzer.log|$LOG_DIR/seclyzer.log|g" "$CONFIG_FILE"

chown "$ACTUAL_USER":"$ACTUAL_USER" "$CONFIG_FILE"

echo -e "${GREEN}✓${NC} Configuration installed"

# ===== Create Systemd Services =====
echo ""
echo "Creating systemd services..."

# Keyboard Collector Service
cat > /etc/systemd/system/seclyzer-keyboard.service << EOF
[Unit]
Description=SecLyzer Keyboard Collector
After=network.target redis-server.service
Requires=redis-server.service

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

# Mouse Collector Service
cat > /etc/systemd/system/seclyzer-mouse.service << EOF
[Unit]
Description=SecLyzer Mouse Collector
After=network.target redis-server.service
Requires=redis-server.service

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

# App Monitor Service
cat > /etc/systemd/system/seclyzer-app.service << EOF
[Unit]
Description=SecLyzer App Monitor
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=$SUDO_USER
Environment="DISPLAY=:0"
ExecStart=$INSTALL_DIR/bin/app_monitor
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo -e "${GREEN}✓${NC} Systemd services created"

# ===== Install Helper Scripts =====
echo ""
echo "Installing helper scripts..."
cp scripts/seclyzer "$INSTALL_DIR/bin/"
chmod +x "$INSTALL_DIR/bin/seclyzer"

# Copy Python modules
echo "Copying Python modules..."
cp -r "$SOURCE_DIR/storage" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/processing" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/common" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/training" "$INSTALL_DIR/"

# Copy extractor scripts
cp scripts/start_extractors.sh "$INSTALL_DIR/bin/"
cp scripts/stop_extractors.sh "$INSTALL_DIR/bin/"
chmod +x "$INSTALL_DIR/bin/start_extractors.sh"
chmod +x "$INSTALL_DIR/bin/stop_extractors.sh"

echo -e "${GREEN}✓${NC} Helper scripts installed"

# ===== Enable Systemd Services (if enabled) =====
if [ "$ENABLE_AUTOSTART" = true ]; then
    echo ""
    echo "Enabling systemd services for auto-start..."
    systemctl enable seclyzer-keyboard.service
    systemctl enable seclyzer-mouse.service
    systemctl enable seclyzer-app.service
    echo -e "${GREEN}✓${NC} Systemd services enabled"
fi

# ===== Save installation metadata =====
cat > "$INSTALL_DIR/.install_metadata" << EOF
INSTALL_DIR=$INSTALL_DIR
DATA_DIR=$DATA_DIR
LOG_DIR=$LOG_DIR
CONFIG_DIR=$CONFIG_DIR
PYTHON_VENV_PATH=$PYTHON_VENV_PATH
INSTALLED_USER=$ACTUAL_USER
INSTALL_DATE=$(date)
REDIS_INSTALLED=$INSTALL_REDIS
AUTOSTART_ENABLED=$ENABLE_AUTOSTART
PASSWORD_HASH=$SECLYZER_PASSWORD_HASH
EOF

# Save password hash separately (more secure location)
echo "$SECLYZER_PASSWORD_HASH" > "$CONFIG_DIR/.password_hash"
chmod 600 "$CONFIG_DIR/.password_hash"

# ===== Create uninstall script =====
echo ""
echo "Creating uninstall script..."

cat > "$INSTALL_DIR/uninstall.sh" << 'UNINSTALL_SCRIPT_EOF'
#!/bin/bash
# SecLyzer Uninstall Script
# Auto-generated during installation

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

# Load installation metadata
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.install_metadata" ]; then
    source "$SCRIPT_DIR/.install_metadata"
else
    echo -e "${RED}✗ Installation metadata not found${NC}"
    exit 1
fi

echo -e "${YELLOW}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║       SecLyzer Uninstallation                     ║${NC}"
echo -e "${YELLOW}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

echo "This will remove SecLyzer from your system."
echo ""
echo "The following will be removed:"
echo "  - Binaries in: $INSTALL_DIR"
echo "  - Configuration: $CONFIG_DIR"
echo "  - Systemd services (if enabled)"
echo ""

read -p "Remove data directory ($DATA_DIR)? This includes trained models! [y/N]: " remove_data
read -p "Remove logs ($LOG_DIR)? [y/N]: " remove_logs
read -p "Uninstall Redis? [y/N]: " uninstall_redis

echo ""

# Require password
password_file="$CONFIG_DIR/.password_hash"
if [ -f "$password_file" ]; then
    stored_hash=$(cat "$password_file")
    
    echo "Password verification required for uninstallation."
    read -s -p "Enter SecLyzer password: " entered_password
    echo ""
    
    entered_hash=$(echo -n "$entered_password" | sha256sum | cut -d' ' -f1)
    
    if [ "$entered_hash" != "$stored_hash" ]; then
        echo -e "${RED}✗ Incorrect password. Uninstallation cancelled.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Password verified"
    echo ""
fi

echo -e "${RED}⚠ WARNING: This action cannot be undone!${NC}"
read -p "Proceed with uninstallation? [y/N]: " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo ""
echo "Uninstalling SecLyzer..."
echo ""

# Stop and disable services
if [ "$AUTOSTART_ENABLED" = true ]; then
    echo "Stopping services..."
    systemctl stop seclyzer-keyboard.service 2>/dev/null || true
    systemctl stop seclyzer-mouse.service 2>/dev/null || true
    systemctl stop seclyzer-app.service 2>/dev/null || true
    
    systemctl disable seclyzer-keyboard.service 2>/dev/null || true
    systemctl disable seclyzer-mouse.service 2>/dev/null || true
    systemctl disable seclyzer-app.service 2>/dev/null || true
    
    rm -f /etc/systemd/system/seclyzer-*.service
    systemctl daemon-reload
    
    echo -e "${GREEN}✓${NC} Services stopped and removed"
fi

# Remove binaries
echo "Removing binaries..."
rm -rf "$INSTALL_DIR"
echo -e "${GREEN}✓${NC} Binaries removed"

# Remove configuration
echo "Removing configuration..."
rm -rf "$CONFIG_DIR"
echo -e "${GREEN}✓${NC} Configuration removed"

# Remove data (if confirmed)
if [[ "$remove_data" =~ ^[Yy]$ ]]; then
    echo "Removing data directory..."
    rm -rf "$DATA_DIR"
    echo -e "${GREEN}✓${NC} Data removed"
else
    echo -e "${YELLOW}⚠${NC} Data directory preserved: $DATA_DIR"
fi

# Remove logs (if confirmed)
if [[ "$remove_logs" =~ ^[Yy]$ ]]; then
    echo "Removing logs..."
    rm -rf "$LOG_DIR"
    echo -e "${GREEN}✓${NC} Logs removed"
else
    echo -e "${YELLOW}⚠${NC} Log directory preserved: $LOG_DIR"
fi

# Uninstall Redis (if confirmed and was installed by SecLyzer)
if [[ "$uninstall_redis" =~ ^[Yy]$ ]] && [ "$REDIS_INSTALLED" = true ]; then
    echo "Uninstalling Redis..."
    systemctl stop redis-server
    systemctl disable redis-server
    apt remove -y redis-server redis-tools
    apt autoremove -y
    echo -e "${GREEN}✓${NC} Redis uninstalled"
else
    echo -e "${YELLOW}⚠${NC} Redis preserved"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   SecLyzer has been uninstalled successfully      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

if [[ ! "$remove_data" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Note: Your data is still at: $DATA_DIR${NC}"
fi

UNINSTALL_SCRIPT_EOF

chmod +x "$INSTALL_DIR/uninstall.sh"

echo -e "${GREEN}✓${NC} Uninstall script created at: $INSTALL_DIR/uninstall.sh"

# ===== Final Summary =====
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  SecLyzer Installation Complete!                 ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

echo "Installation Summary:"
echo "  ✓ Collectors installed to: $INSTALL_DIR/bin/"
echo "  ✓ Configuration: $CONFIG_DIR/seclyzer.yml"
echo "  ✓ Data directory: $DATA_DIR"
echo "  ✓ Log directory: $LOG_DIR"

if [ "$INSTALL_REDIS" = true ]; then
    echo "  ✓ Redis configured (${REDIS_MEMORY} memory limit)"
fi

if [ "$ENABLE_AUTOSTART" = true ]; then
    echo "  ✓ Systemd services enabled"
fi

echo ""
echo "Next Steps:"
echo ""
echo "1. Test the installation:"
echo "   See: $(pwd)/docs/PHASE1_TESTING.md"
echo ""

if [ "$ENABLE_AUTOSTART" = true ]; then
    echo "2. Start services:"
    echo "   sudo systemctl start seclyzer-keyboard"
    echo "   sudo systemctl start seclyzer-mouse"
    echo "   sudo systemctl start seclyzer-app"
    echo ""
    echo "3. Check status:"
    echo "   sudo systemctl status seclyzer-*"
    echo ""
else
    echo "2. Manually run collectors:"
    echo "   sudo $INSTALL_DIR/bin/keyboard_collector"
    echo "   sudo $INSTALL_DIR/bin/mouse_collector"
    echo "   $INSTALL_DIR/bin/app_monitor"
    echo ""
fi

echo "To uninstall:"
echo "  sudo $INSTALL_DIR/uninstall.sh"
echo ""

echo -e "${YELLOW}⚠ IMPORTANT: Keyboard and mouse collectors require root permissions!${NC}"
echo ""
