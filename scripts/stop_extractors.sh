#!/bin/bash
# ============================================================================
# SecLyzer Feature Extractors Stop Script
# ============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Stopping SecLyzer Feature Extractors..."

pkill -f "keystroke_extractor.py" 2>/dev/null && echo -e "${GREEN}✓${NC} Keystroke extractor stopped" || echo -e "${YELLOW}⚠${NC} Keystroke extractor not running"
pkill -f "mouse_extractor.py" 2>/dev/null && echo -e "${GREEN}✓${NC} Mouse extractor stopped" || echo -e "${YELLOW}⚠${NC} Mouse extractor not running"
pkill -f "app_tracker.py" 2>/dev/null && echo -e "${GREEN}✓${NC} App tracker stopped" || echo -e "${YELLOW}⚠${NC} App tracker not running"

echo ""
echo -e "${GREEN}✓ Feature extractors stopped${NC}"
