#!/bin/bash
# Quick build script for all collectors

set -e

echo "=== Building SecLyzer Collectors ==="
echo ""

cd "$(dirname "$0")/../collectors"

echo "1/3 Building keyboard collector..."
cd keyboard_collector
cargo build --release
echo "✓ Keyboard collector built"
echo ""

echo "2/3 Building mouse collector..."
cd ../mouse_collector
cargo build --release
echo "✓ Mouse collector built"
echo ""

echo "3/3 Building app monitor..."
cd ../app_monitor
cargo build --release
echo "✓ App monitor built"
echo ""

echo "=== Build Complete ==="
echo ""
echo "Binaries are located at:"
echo "  collectors/keyboard_collector/target/release/keyboard_collector"
echo "  collectors/mouse_collector/target/release/mouse_collector"
echo "  collectors/app_monitor/target/release/app_monitor"
echo ""
echo "Next steps:"
echo "  1. Run: ./scripts/setup_redis.sh"
echo "  2. See: docs/PHASE1_TESTING.md for testing instructions"
