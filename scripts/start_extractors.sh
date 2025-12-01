#!/bin/bash
# Start SecLyzer Feature Extractors

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REAL_USER="${SUDO_USER:-$USER}"
VENV_PATH="/home/$REAL_USER/Documents/Projects/venv"
LOG_DIR="/var/log/seclyzer"

echo -e "${GREEN}Starting SecLyzer Feature Extractors...${NC}"
echo ""

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}✗ Virtual environment not found at: $VENV_PATH${NC}"
    echo "Please create it or update VENV_PATH in this script"
    exit 1
fi

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Check if already running
if pgrep -f "keystroke_extractor.py" > /dev/null; then
    echo -e "${YELLOW}⚠ Keystroke extractor already running${NC}"
else
    echo "Starting keystroke extractor..."
    sudo -u "$REAL_USER" bash -c "
        source '$VENV_PATH/bin/activate'
        export PYTHONPATH='$PROJECT_ROOT:\$PYTHONPATH'
        cd '$PROJECT_ROOT'
        nohup python3 -u processing/extractors/keystroke_extractor.py > '$LOG_DIR/keystroke_extractor.log' 2>&1 &
    "
    echo -e "${GREEN}✓${NC} Keystroke extractor started"
fi

if pgrep -f "mouse_extractor.py" > /dev/null; then
    echo -e "${YELLOW}⚠ Mouse extractor already running${NC}"
else
    echo "Starting mouse extractor..."
    sudo -u "$REAL_USER" bash -c "
        source '$VENV_PATH/bin/activate'
        export PYTHONPATH='$PROJECT_ROOT:\$PYTHONPATH'
        cd '$PROJECT_ROOT'
        nohup python3 -u processing/extractors/mouse_extractor.py > '$LOG_DIR/mouse_extractor.log' 2>&1 &
    "
    echo -e "${GREEN}✓${NC} Mouse extractor started"
fi

# Check if on X11 (app monitor only works on X11)
if [ -n "$DISPLAY" ] && ! pgrep -x "wayland" > /dev/null 2>&1; then
    if pgrep -f "app_tracker.py" > /dev/null; then
        echo -e "${YELLOW}⚠ App tracker already running${NC}"
    else
        echo "Starting app tracker..."
        sudo -u "$REAL_USER" bash -c "
            source '$VENV_PATH/bin/activate'
            export PYTHONPATH='$PROJECT_ROOT:\$PYTHONPATH'
            cd '$PROJECT_ROOT'
            nohup python3 -u processing/extractors/app_tracker.py > '$LOG_DIR/app_tracker.log' 2>&1 &
        "
        echo -e "${GREEN}✓${NC} App tracker started"
    fi
else
    echo -e "${YELLOW}⚠ Skipping app tracker (Wayland detected or no X11)${NC}"
fi

echo ""
echo -e "${GREEN}✓ Feature extractors started${NC}"
echo ""
echo "View logs:"
echo "  tail -f $LOG_DIR/keystroke_extractor.log"
echo "  tail -f $LOG_DIR/mouse_extractor.log"
echo "  tail -f $LOG_DIR/app_tracker.log"
echo ""
echo "To stop extractors:"
echo "  sudo $PROJECT_ROOT/scripts/stop_extractors.sh"
