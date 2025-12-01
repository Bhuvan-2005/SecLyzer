#!/bin/bash
# Start SecLyzer Rust Collectors (Manual Mode)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/var/log/seclyzer"

echo -e "${GREEN}Starting SecLyzer Collectors...${NC}"
echo ""

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Start keyboard collector
if pgrep -f "keyboard_collector" > /dev/null; then
    echo -e "${YELLOW}⚠ Keyboard collector already running${NC}"
else
    echo "Starting keyboard collector..."
    nohup "$PROJECT_ROOT/collectors/keyboard_collector/target/release/keyboard_collector" > "$LOG_DIR/keyboard_collector.log" 2>&1 &
    echo -e "${GREEN}✓${NC} Keyboard collector started (PID: $!)"
fi

# Start mouse collector
if pgrep -f "mouse_collector" > /dev/null; then
    echo -e "${YELLOW}⚠ Mouse collector already running${NC}"
else
    echo "Starting mouse collector..."
    nohup "$PROJECT_ROOT/collectors/mouse_collector/target/release/mouse_collector" > "$LOG_DIR/mouse_collector.log" 2>&1 &
    echo -e "${GREEN}✓${NC} Mouse collector started (PID: $!)"
fi

# Start app monitor (X11 only)
if [ -n "$DISPLAY" ] && ! pgrep -x "wayland" > /dev/null 2>&1; then
    if pgrep -f "app_monitor" > /dev/null; then
        echo -e "${YELLOW}⚠ App monitor already running${NC}"
    else
        echo "Starting app monitor..."
        nohup "$PROJECT_ROOT/collectors/app_monitor/target/release/app_monitor" > "$LOG_DIR/app_monitor.log" 2>&1 &
        echo -e "${GREEN}✓${NC} App monitor started (PID: $!)"
    fi
else
    echo -e "${YELLOW}⚠ Skipping app monitor (Wayland detected or no X11)${NC}"
fi

echo ""
echo -e "${GREEN}✓ Collectors started${NC}"
echo ""
echo "View logs:"
echo "  tail -f $LOG_DIR/keyboard_collector.log"
echo "  tail -f $LOG_DIR/mouse_collector.log"
echo "  tail -f $LOG_DIR/app_monitor.log"
echo ""
echo "To stop collectors:"
echo "  sudo $PROJECT_ROOT/scripts/stop_collectors.sh"
