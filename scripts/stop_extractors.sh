#!/bin/bash
# Stop SecLyzer Feature Extractors

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping SecLyzer Feature Extractors...${NC}"
echo ""

# Stop extractors
pkill -f "keystroke_extractor.py" && echo -e "${GREEN}✓${NC} Keystroke extractor stopped" || echo "  Keystroke extractor not running"
pkill -f "mouse_extractor.py" && echo -e "${GREEN}✓${NC} Mouse extractor stopped" || echo "  Mouse extractor not running"
pkill -f "app_tracker.py" && echo -e "${GREEN}✓${NC} App tracker stopped" || echo "  App tracker not running"

echo ""
echo -e "${GREEN}✓ Feature extractors stopped${NC}"
