# SecLyzer Control Guide

## Quick On/Off Switch

SecLyzer includes a simple control script for easy management.

### Installation

The control script is installed at:
- Development: `scripts/seclyzer`
- Installed: `/usr/local/bin/seclyzer` (after install.sh)

### Basic Commands

```bash
# Start SecLyzer
sudo ./scripts/seclyzer start

# Stop SecLyzer
sudo ./scripts/seclyzer stop

# Check status
./scripts/seclyzer status

# Restart
sudo ./scripts/seclyzer restart
```

### Detailed Usage

#### Start SecLyzer

```bash
sudo ./scripts/seclyzer start
```

**What it does:**
- ✅ Starts Redis (if stopped)
- ✅ Starts InfluxDB (if stopped)
- ✅ Starts collectors (keyboard, mouse, app)
- ✅ Shows commands to start feature extractors

**Output:**
```
Starting SecLyzer...

Starting Redis...
Starting InfluxDB...
Starting collectors...
✓ Collectors started via systemd

✓ SecLyzer started
```

#### Stop SecLyzer

```bash
sudo ./scripts/seclyzer stop
```

**What it does:**
- ✅ Stops all collectors
- ✅ Stops feature extractors
- ⚠️ Asks if you want to stop databases

**Output:**
```
Stopping SecLyzer...

Stopping systemd services...
✓ Systemd services stopped

Stopping feature extractors...
✓ Feature extractors stopped

✓ SecLyzer stopped

Stop Redis and InfluxDB too? [y/N]:
```

**Tip:** Answer "N" if you want databases to keep running (saves startup time)

#### Check Status

```bash
./scripts/seclyzer status
```

**Shows:**
- All collector statuses (RUNNING/STOPPED)
- Feature extractor statuses
- Redis status
- InfluxDB status

**Example output:**
```
╔═══════════════════════════════════════════════════╗
║         SecLyzer Status                           ║
╚═══════════════════════════════════════════════════╝

Mode: Systemd Services

● seclyzer-keyboard.service - SecLyzer Keyboard Collector
   Active: active (running)

● seclyzer-mouse.service - SecLyzer Mouse Collector
   Active: active (running)

● seclyzer-app.service - SecLyzer App Monitor
   Active: active (running)

Redis: RUNNING
InfluxDB: RUNNING
```

#### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot
sudo ./scripts/seclyzer enable

# Disable auto-start
sudo ./scripts/seclyzer disable
```

**Note:** Requires systemd services (installed via install.sh)

---

## Common Scenarios

### Scenario 1: Quick Testing Session

```bash
# Start everything
sudo ./scripts/seclyzer start

# ... do your work ...

# Stop when done
sudo ./scripts/seclyzer stop
```

### Scenario 2: Persistent Background Service

```bash
# Enable auto-start
sudo ./scripts/seclyzer enable

# Start now
sudo ./scripts/seclyzer start

# Now SecLyzer runs automatically at boot
```

### Scenario 3: Debugging (Stop During Development)

```bash
# Stop SecLyzer temporarily
sudo ./scripts/seclyzer stop

# Make code changes...

# Restart with new code
sudo ./scripts/seclyzer restart
```

### Scenario 4: Check If Running

```bash
# Quick status check
./scripts/seclyzer status

# Or use system tools
systemctl status seclyzer-*
```

---

## Manual Control (Alternative)

If you prefer manual control or systemd isn't available:

### Start Collectors Manually

```bash
# Terminal 1
sudo collectors/keyboard_collector/target/release/keyboard_collector

# Terminal 2
sudo collectors/mouse_collector/target/release/mouse_collector

# Terminal 3
collectors/app_monitor/target/release/app_monitor
```

### Start Feature Extractors

```bash
source /home/bhuvan/Documents/Projects/venv/bin/activate

# Terminal 4
python3 processing/extractors/keystroke_extractor.py

# Terminal 5
python3 processing/extractors/mouse_extractor.py

# Terminal 6
python3 processing/extractors/app_tracker.py
```

### Stop Everything

Press `Ctrl+C` in each terminal, or:

```bash
pkill -f keyboard_collector
pkill -f mouse_collector
pkill -f app_monitor
pkill -f keystroke_extractor
pkill -f mouse_extractor
pkill -f app_tracker
```

---

## Integration with Install Script

During installation, the control script is copied to:

```bash
/usr/local/bin/seclyzer
```

This allows you to use it from anywhere:

```bash
# From any directory
sudo seclyzer start
sudo seclyzer stop
seclyzer status
```

---

## Troubleshooting

### "Permission denied"

Use `sudo` for start/stop commands:
```bash
sudo ./scripts/seclyzer start
```

### "Systemd services not installed"

If you see this warning:
```
⚠ Systemd services not installed
Please start collectors manually or run install.sh with systemd enabled
```

Either:
1. Run collectors manually (see above)
2. Re-run `install.sh` and enable systemd

### Services won't start

Check dependencies:
```bash
# Check Redis
sudo systemctl status redis-server

# Check InfluxDB
sudo systemctl status influxdb
```

### Can't find control script

From project directory:
```bash
./scripts/seclyzer status
```

After installation:
```bash
seclyzer status  # If /usr/local/bin is in PATH
```

---

## Developer Mode Integration

The control script works with developer mode:

```bash
# Activate dev mode
touch /tmp/.seclyzer_dev_mode

# Start SecLyzer (will run with dev mode active)
sudo ./scripts/seclyzer start

# Check status (shows dev mode in logs)
./scripts/seclyzer status

# Deactivate dev mode
rm /tmp/.seclyzer_dev_mode
```

---

## Summary

**Simple on/off switch:**
```bash
sudo ./scripts/seclyzer start   # Turn ON
sudo ./scripts/seclyzer stop    # Turn OFF
./scripts/seclyzer status       # Check status
```

**That's it! No need to remember complex systemctl commands.**
