# SecLyzer Installation Guide

## Quick Install (Recommended)

Run the interactive installer:

```bash
cd /home/bhuvan/Documents/Projects/SecLyzer
sudo ./install.sh
```

The installer will guide you through:
1. **Installation paths** (binaries, data, logs, config)
2. **Redis configuration** (memory limits)
3. **Python environment** (virtual env path)
4. **System integration** (auto-start on boot)

## Installation Options

### Customizable Paths

| What | Default | Purpose |
|------|---------|---------|
| Binaries | `/opt/seclyzer` | Collector executables |
| Data | `/var/lib/seclyzer` | Models, databases |
| Logs | `/var/log/seclyzer` | System logs |
| Config | `/etc/seclyzer` | Configuration files |

### What Gets Installed

1. **System Dependencies:**
   - build-essential, pkg-config
   - X11 libraries (libx11-dev, libxext-dev, libxtst-dev)
   - Python 3 + pip + venv
   - Redis server (optional)

2. **Rust (if not present):**
   - Automatically installed using rustup
   - Installed for the regular user (not root)

3. **SecLyzer Collectors:**
   - Keyboard collector (Rust binary)
   - Mouse collector (Rust binary)
   - App monitor (Rust binary)

4. **Python Dependencies (in venv):**
   - redis (Redis client)
   - polars (Fast DataFrame library)
   - influxdb-client (Time-series database)
   - scikit-learn (Machine learning)

5. **System Services (optional):**
   - systemd services for auto-start
   - seclyzer-keyboard.service
   - seclyzer-mouse.service
   - seclyzer-app.service

## Installation Modes

### Mode 1: Full System Install (Default)

- Installs to system directories (`/opt`, `/var/lib`, etc.)
- Creates systemd services
- Auto-starts on boot
- Requires sudo

**Best for:** Permanent installation, production use

### Mode 2: Manual Install (No auto-start)

Answer "No" to auto-start during installation.

- Installs binaries
- No systemd services
- Run collectors manually

**Best for:** Testing, development

### Mode 3: Skip Redis

Answer "No" to Redis installation if you already have it configured.

**Best for:** Advanced users with existing Redis setup

## Post-Installation

### Check Installation

```bash
# Check binaries
ls -l /opt/seclyzer/bin/

# Check services (if enabled)
sudo systemctl status seclyzer-*

# Check Redis
redis-cli ping
```

### Start Collectors (Manual Mode)

If you disabled auto-start:

```bash
# Terminal 1
sudo /opt/seclyzer/bin/keyboard_collector

# Terminal 2
sudo /opt/seclyzer/bin/mouse_collector

# Terminal 3
/opt/seclyzer/bin/app_monitor  # No sudo needed
```

### Start Collectors (Auto-start Mode)

```bash
sudo systemctl start seclyzer-keyboard
sudo systemctl start seclyzer-mouse
sudo systemctl start seclyzer-app
```

### View Logs

```bash
# System logs (if using systemd)
sudo journalctl -u seclyzer-keyboard -f
sudo journalctl -u seclyzer-mouse -f
sudo journalctl -u seclyzer-app -f

# Application logs (Phase 2+)
tail -f /var/log/seclyzer/seclyzer.log
```

## Uninstallation

The installer creates an uninstall script at installation time.

```bash
sudo /opt/seclyzer/uninstall.sh
```

This will:
1. Stop all running services
2. Disable systemd services
3. Remove binaries
4. Ask if you want to remove data
5. Ask if you want to remove logs
6. Ask if you want to uninstall Redis

**Data and logs are preserved by default** unless you explicitly confirm deletion.

### Manual Uninstall (if uninstall.sh is missing)

```bash
# Stop services
sudo systemctl stop seclyzer-*
sudo systemctl disable seclyzer-*
sudo rm /etc/systemd/system/seclyzer-*.service
sudo systemctl daemon-reload

# Remove files
sudo rm -rf /opt/seclyzer
sudo rm -rf /etc/seclyzer
sudo rm -rf /var/lib/seclyzer  # Warning: removes trained models!
sudo rm -rf /var/log/seclyzer
```

## Troubleshooting

### "Rust not found"

The installer should auto-install Rust. If it fails:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### "Redis connection failed"

```bash
# Check if Redis is running
sudo systemctl status redis-server

# Start Redis
sudo systemctl start redis-server

# Test connection
redis-cli ping
```

### "Permission denied" for collectors

Keyboard and mouse collectors need root:

```bash
sudo /opt/seclyzer/bin/keyboard_collector
```

### "X11 connection failed" (App monitor)

Make sure you're on X11, not Wayland:

```bash
echo $XDG_SESSION_TYPE
# Should output: x11
```

If Wayland, log out and select "Ubuntu on Xorg" at login screen.

### Services fail to start

```bash
# Check service status
sudo systemctl status seclyzer-keyboard

# View detailed logs
sudo journalctl -u seclyzer-keyboard -n 50
```

Common issues:
- Redis not running → `sudo systemctl start redis-server`
- X11 not available → Run app_monitor in user session, not as service
- Permissions → Keyboard/mouse collectors must run as root

## Upgrade Process

To upgrade SecLyzer to a new version:

1. **Backup your data:**
   ```bash
   sudo cp -r /var/lib/seclyzer ~/seclyzer-backup
   ```

2. **Stop services:**
   ```bash
   sudo systemctl stop seclyzer-*
   ```

3. **Pull new code:**
   ```bash
   cd /home/bhuvan/Documents/Projects/SecLyzer
   git pull  # Or download new version
   ```

4. **Run installer again:**
   ```bash
   sudo ./install.sh
   ```
   
   It will detect existing installation and ask if you want to overwrite.

5. **Restart services:**
   ```bash
   sudo systemctl start seclyzer-*
   ```

## Security Notes

### Permissions

- Keyboard/mouse collectors: Run as root (need `/dev/input` access)
- App monitor: Runs as regular user
- Data directory: Owned by regular user
- Config files: Readable by regular user

### Network Exposure

- Redis: Bound to 127.0.0.1 only (localhost)
- No external network ports opened
- All data stays local

### Data Protection

1. **Encrypt data directory:**
   ```bash
   # Use LUKS or ecryptfs for /var/lib/seclyzer
   ```

2. **Secure config:**
   ```bash
   sudo chmod 600 /etc/seclyzer/seclyzer.yml
   ```

## Advanced Configuration

After installation, edit the config file:

```bash
sudo nano /etc/seclyzer/seclyzer.yml
```

Key settings:
- `fusion.weights`: Adjust model importance
- `decision.thresholds`: Tune sensitivity
- `privacy.store_actual_keys`: Enable/disable key logging (default: false)
- `performance.collector_sleep_ms`: Polling interval

Restart services after config changes:

```bash
sudo systemctl restart seclyzer-*
```
