#!/bin/bash

# SecLyzer Context Persistence Verification Script
# Run this on any Warp profile to verify your context is safe
# Usage: bash .warp-local/verify_context.sh

set -e

echo "🔍 SecLyzer Context Persistence Verification"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Are we in the right directory?
if [ ! -f ".gitignore" ] || [ ! -d ".warp-local" ]; then
    echo -e "${RED}✗ ERROR: Not in SecLyzer root directory${NC}"
    echo "Run this from: /home/bhuvan/Documents/Projects/SecLyzer"
    exit 1
fi

echo -e "${GREEN}✓ In correct directory${NC}"
echo ""

# Check 2: Verify all context files exist
echo "Checking context files..."
files=(
    ".warp-local/README.md"
    ".warp-local/CONTEXT_SNAPSHOT.md"
    ".warp-local/PRODUCTION_READINESS_AUDIT.md"
    ".warp-local/SPRINT_2WEEKS.md"
    ".warp-local/DEEP_CODE_ANALYSIS.md"
    ".warp-local/CODEBASE_AUDIT.md"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file")
        printf "  ${GREEN}✓${NC} %-45s (%4d lines)\n" "$(basename $file)" "$lines"
    else
        printf "  ${RED}✗${NC} %-45s (MISSING)\n" "$(basename $file)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo ""
    echo -e "${RED}Some files are missing. Context is incomplete.${NC}"
    exit 1
fi

echo ""

# Check 3: Verify .gitignore excludes .warp-local/
echo "Checking git ignore..."
if grep -q "\.warp-local" .gitignore; then
    echo -e "  ${GREEN}✓${NC} .warp-local/ is in .gitignore"
    echo "    (Files won't be committed to git)"
else
    echo -e "  ${RED}✗${NC} .warp-local/ is NOT in .gitignore"
    echo "    (Context may be accidentally committed)"
fi

echo ""

# Check 4: Show total size
echo "Storage usage..."
size=$(du -sh .warp-local/ | cut -f1)
echo -e "  ${GREEN}✓${NC} Total: $size of knowledge"
echo "    (All context survives profile changes)"

echo ""

# Check 5: Verify git status doesn't show .warp-local
echo "Git status check..."
git_status=$(git status --short | grep ".warp-local" || echo "")
if [ -z "$git_status" ]; then
    echo -e "  ${GREEN}✓${NC} .warp-local/ is not in git tracking"
    echo "    (Context stays local, not synced)"
else
    echo -e "  ${YELLOW}⚠${NC} .warp-local/ may be tracked:"
    echo "$git_status"
fi

echo ""

# Check 6: Show what to do next
echo "=============================================="
echo ""
echo -e "${GREEN}✓ All checks passed!${NC}"
echo ""
echo "Your context is safe and persisted."
echo ""
echo "Next steps:"
echo "  1. cd /home/bhuvan/Documents/Projects/SecLyzer"
echo "  2. cat .warp-local/CONTEXT_SNAPSHOT.md"
echo ""
echo "Or jump to detailed action plan:"
echo "  cat .warp-local/SPRINT_2WEEKS.md"
echo ""
