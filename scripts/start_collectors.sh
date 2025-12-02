#!/bin/bash
# ============================================================================
# SecLyzer Rust Collectors Startup Script
# Automatically detects binaries and starts all collectors
# ============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Detect project root and binary locations
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Possible binary locations
find_binary() {
    local name=$1
    local paths=(
        "$PROJECT_ROOT/collectors/$name/target/release/$name"
        "/opt/seclyzer/bin/$name"
        "/usr/local/bin/$name"
    )
    
    for p in "${paths[@]}"; do
        if [ -x "$p" ]; then
            echo "$p"
            return 0
        fi
    done
    
    return 1
}

# Log directory
LOG_DIR="${SECLYZER_LOG_DIR:-/var/log/seclyzer}"
mkdir -p "$LOG_DIR" 2>/dev/null || true

echo -e "${GREEN}Starting SecLyzer Collectors...${NC}"
echo ""

# Check if running as root (required for keyboard/mouse)
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}⚠ Warning: Keyboard and mouse collectors require root privileges${NC}"
    echo "  Run with: sudo $0"
    echo ""
fi

# Start keyboard collector
KEYBOARD_BIN=$(find_binary "keyboard_collector") || {
    echo -e "${RED}✗${NC} keyboard_collector binary not found"
    echo "  Build with: cd collectors/keyboard_collector && cargo build --release"
}

if [ -n "$KEYBOARD_BIN" ]; then
    if pgrep -f "keyboard_collector" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} Keyboard collector already running"
    else
        echo -n "Starting keyboard collector... "
        nohup "$KEYBOARD_BIN" > "$LOG_DIR/keyboard_collector.log" 2>&1 &
        sleep 1
        if pgrep -f "keyboard_collector" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} (PID: $!)"
        else
            echo -e "${RED}✗${NC}"
        fi
    fi
fi

# Start mouse collector
MOUSE_BIN=$(find_binary "mouse_collector") || {
    echo -e "${RED}✗${NC} mouse_collector binary not found"
}

if [ -n "$MOUSE_BIN" ]; then
    if pgrep -f "mouse_collector" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} Mouse collector already running"
    else
        echo -n "Starting mouse collector... "
        nohup "$MOUSE_BIN" > "$LOG_DIR/mouse_collector.log" 2>&1 &
        sleep 1
        if pgrep -f "mouse_collector" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} (PID: $!)"
        else
            echo -e "${RED}✗${NC}"
        fi
    fi
fi

# Start app monitor (X11 only)
if [ -n "$DISPLAY" ]; then
    APP_BIN=$(find_binary "app_monitor") || {
        echo -e "${RED}✗${NC} app_monitor binary not found"
    }
    
    if [ -n "$APP_BIN" ]; then
        if pgrep -f "app_monitor" > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠${NC} App monitor already running"
        else
            echo -n "Starting app monitor... "
            # App monitor doesn't need root
            REAL_USER="${SUDO_USER:-$USER}"
            if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
                sudo -u "$REAL_USER" nohup "$APP_BIN" > "$LOG_DIR/app_monitor.log" 2>&1 &
            else
                nohup "$APP_BIN" > "$LOG_DIR/app_monitor.log" 2>&1 &
            fi
            sleep 1
            if pgrep -f "app_monitor" > /dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} (PID: $!)"
            else
                echo -e "${RED}✗${NC}"
            fi
        fi
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipping app monitor (no DISPLAY - Wayland or headless)"
fi

echo ""
echo -e "${GREEN}✓ Collectors started${NC}"
echo ""
echo "View logs:"
echo "  tail -f $LOG_DIR/keyboard_collector.log"
echo "  tail -f $LOG_DIR/mouse_collector.log"
echo "  tail -f $LOG_DIR/app_monitor.log"
