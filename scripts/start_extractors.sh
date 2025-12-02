#!/bin/bash
# ============================================================================
# SecLyzer Feature Extractors Startup Script
# Automatically detects environment and starts all extractors
# ============================================================================

# Don't exit on error - handle errors ourselves
set +e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/../processing" ]; then
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -d "/opt/seclyzer/lib/processing" ]; then
    PROJECT_ROOT="/opt/seclyzer/lib"
else
    PROJECT_ROOT="$SCRIPT_DIR/.."
fi

# Detect user
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

# Auto-detect virtual environment
detect_venv() {
    local paths=(
        "$VENV_PATH"
        "$REAL_HOME/Documents/Projects/venv"
        "$REAL_HOME/.seclyzer-venv"
        "$REAL_HOME/.venv"
        "$REAL_HOME/venv"
        "/opt/seclyzer/venv"
    )
    
    for p in "${paths[@]}"; do
        if [ -n "$p" ] && [ -d "$p" ] && [ -f "$p/bin/activate" ]; then
            echo "$p"
            return 0
        fi
    done
    
    return 1
}

VENV_PATH=$(detect_venv) || {
    echo -e "${RED}✗ Could not find Python virtual environment${NC}"
    echo "Please set VENV_PATH environment variable"
    exit 1
}

# Log directory
LOG_DIR="${SECLYZER_LOG_DIR:-/var/log/seclyzer}"
mkdir -p "$LOG_DIR" 2>/dev/null || true

echo -e "${GREEN}Starting SecLyzer Feature Extractors...${NC}"
echo "  Project: $PROJECT_ROOT"
echo "  Venv: $VENV_PATH"
echo "  Logs: $LOG_DIR"
echo ""

# Function to start extractor
start_extractor() {
    local name=$1
    local script=$2
    local process_name=$3
    
    if pgrep -f "$process_name" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} $name already running"
        return 0
    fi
    
    echo -n "Starting $name... "
    
    if [ "$EUID" -eq 0 ]; then
        # Running as root, switch to real user
        sudo -u "$REAL_USER" bash -c "
            source '$VENV_PATH/bin/activate'
            export PYTHONPATH='$PROJECT_ROOT:\$PYTHONPATH'
            cd '$PROJECT_ROOT'
            nohup python3 -u '$script' > '$LOG_DIR/${process_name}.log' 2>&1 &
        "
    else
        # Running as normal user
        source "$VENV_PATH/bin/activate"
        export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
        cd "$PROJECT_ROOT"
        nohup python3 -u "$script" > "$LOG_DIR/${process_name}.log" 2>&1 &
    fi
    
    sleep 1
    
    if pgrep -f "$process_name" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Start extractors
start_extractor "Keystroke Extractor" "processing/extractors/keystroke_extractor.py" "keystroke_extractor"
start_extractor "Mouse Extractor" "processing/extractors/mouse_extractor.py" "mouse_extractor"

# App tracker only on X11
if [ -n "$DISPLAY" ]; then
    start_extractor "App Tracker" "processing/extractors/app_tracker.py" "app_tracker"
else
    echo -e "${YELLOW}⚠${NC} Skipping App Tracker (no DISPLAY)"
fi

echo ""
echo -e "${GREEN}✓ Feature extractors started${NC}"
echo ""
echo "View logs:"
echo "  tail -f $LOG_DIR/keystroke_extractor.log"
echo "  tail -f $LOG_DIR/mouse_extractor.log"
echo "  tail -f $LOG_DIR/app_tracker.log"
