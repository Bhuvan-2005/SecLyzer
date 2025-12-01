# SecLyzer Control Scripts Documentation

**Last Updated:** 2025-12-01  
**Version:** 0.2.0

---

## Overview

SecLyzer provides two control scripts for managing the system:

1. **`./scripts/seclyzer`** - Production control script (user-facing)
2. **`./scripts/dev`** - Developer management script (development)

---

## 1. Production Script: `./scripts/seclyzer`

### Purpose
User-facing control script for production deployments. Supports both systemd and manual modes.

### Usage
```bash
./scripts/seclyzer <command>
```

### Commands

| Command | Description |
|---------|-------------|
| `start` | Start all SecLyzer services (collectors + databases; extractors started separately) |
| `disable` | Disable authentication (keep data collection running) |
| `enable` | Re-enable authentication |
| `stop-all` | Stop collectors, extractors, and databases (requires password) |
| `restart` | Restart collectors |
| `status` | Show status of collectors, extractors, and databases |
| `resources` | Show resource usage summary |
| `autostart` | Enable auto-start on boot (systemd, if installed) |
| `no-autostart` | Disable auto-start on boot (systemd, if installed) |
| `help` | Show help message |

### Features
- ✅ Systemd integration (automatic detection)
- ✅ Password protection for sensitive commands
- ✅ Manual mode fallback (no systemd required)
- ✅ Auto-start management

### Example
```bash
# Check status
./scripts/seclyzer status

# Start services
./scripts/seclyzer start

# View resource usage
./scripts/seclyzer resources
```

---

## 2. Developer Script: `./scripts/dev`

### Purpose
Comprehensive development console with advanced features for developers working on SecLyzer.

### Usage
```bash
./scripts/dev <command> [options]
```

###Commands by Category

#### 🔧 Service Management
| Command | Description |
|---------|-------------|
| `start` | Start all collectors and extractors |
| `stop` | Stop all SecLyzer processes |
| `restart` | Restart all services |
| `status` | Show detailed component status |
| `logs` | Tail all logs in real-time |

#### 🧪 Development & Testing
| Command | Description |
|---------|-------------|
| `test` | Run pytest suite (if a `tests/` directory is present) |
| `test-coverage` | Run tests with HTML coverage report (if a `tests/` directory is present) |
| `lint` | Run linters (black, flake8, mypy) |
| `format` | Auto-format code (black + isort) |
| `check-health` | Verify all dependencies installed |

#### 📊 Data & Models
| Command | Description |
|---------|-------------|
| `check-data` | Check training data readiness (if `scripts/check_training_readiness.py` is present) |
| `train` | Train ML models (if `scripts/train_models.py` is present; prompts for confirmation) |
| `export-data` | Export collected data to CSV |
| `backup` | Create full system backup |

#### 🐛 Debugging
| Command | Description |
|---------|-------------|
| `debug-redis` | Monitor Redis Pub/Sub events |
| `debug-influx` | Test InfluxDB connection |
| `show-metrics` | Display system metrics (CPU, RAM, data counts) |
| `tail-json-logs` | Parse and display JSON logs |

#### 🧹 Cleanup
| Command | Description |
|---------|-------------|
| `clean-logs` | Remove logs older than 7 days |
| `clean-pycache` | Delete __pycache__ directories |
| `reset-data` | Reset all collected data (DANGEROUS) |

#### ⚙️ Utilities
| Command | Description |
|---------|-------------|
| `config` | Show current configuration |
| `env` | Display SecLyzer environment variables |
| `version` | Show version information |

### Examples

**Quick Status Check:**
```bash
./scripts/dev status
```
Output:
```
═══ SecLyzer System Status ═══

Rust Collectors:
  ✓ keyboard_collector
  ✓ mouse_collector
  ✓ app_monitor

Python Extractors:
  ✓ keystroke_extractor
  ✓ mouse_extractor
  ✓ app_tracker

Databases:
  ✓ Redis (healthy)
  ✓ InfluxDB (healthy)
  ✓ SQLite (file exists)
```

**Run Tests:**
```bash
./scripts/dev test
```

**Check What Data Has Been Collected:**
```bash
./scripts/dev check-data
```

**Monitor Live Events:**
```bash
./scripts/dev debug-redis
```

**View Metrics:**
```bash
./scripts/dev show-metrics
```
Output:
```
═══ System Metrics ═══

Running Processes:
  Collectors: 3
  Extractors: 3

Memory Usage (MB):
  Total: 260.5 MB

Data Collection:
  Keystroke: 839 vectors (8.4%)
  Mouse: 1,248 vectors (8.3%)
  App: 156 events (31.2%)
```

---

## 3. Startup Procedures

### After System Reboot (Manual Mode)

**Option 1: Using production script**
```bash
cd ~/Documents/Projects/SecLyzer
./scripts/seclyzer start
```

**Option 2: Using dev script**
```bash
cd ~/Documents/Projects/SecLyzer
./scripts/dev start
```

**Option 3: Manual (legacy)**
```bash
cd ~/Documents/Projects/SecLyzer
./scripts/start_collectors.sh
./scripts/start_extractors.sh
```

### With Systemd (Future)
```bash
# Once systemd services are installed:
systemctl start seclyzer-*
```

---

## 4. Environment Variables

Both scripts respect the following environment variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `REDIS_PASSWORD` | Redis authentication | `export REDIS_PASSWORD="secret"` |
| `REDIS_HOST` | Redis server address | `export REDIS_HOST="localhost"` |
| `REDIS_PORT` | Redis server port | `export REDIS_PORT="6379"` |
| `INFLUX_URL` | InfluxDB URL | `export INFLUX_URL="http://localhost:8086"` |
| `INFLUX_TOKEN` | InfluxDB auth token | `export INFLUX_TOKEN="my-token"` |
| `INFLUX_ORG` | InfluxDB organization | `export INFLUX_ORG="seclyzer"` |
| `INFLUX_BUCKET` | InfluxDB bucket name | `export INFLUX_BUCKET="seclyzer"` |
| `SECLYZER_LOG_LEVEL` | Log verbosity | `export SECLYZER_LOG_LEVEL="DEBUG"` |
| `VENV_PATH` | Python venv location | `export VENV_PATH="~/venv"` |

---

## 5. Log Locations

| Component | Log File |
|-----------|----------|
| Keyboard Collector | `/var/log/seclyzer/keyboard_collector.log` |
| Mouse Collector | `/var/log/seclyzer/mouse_collector.log` |
| App Monitor | `/var/log/seclyzer/app_monitor.log` |
| Keystroke Extractor | `/var/log/seclyzer/keystroke_extractor.log` |
| Mouse Extractor | `/var/log/seclyzer/mouse_extractor.log` |
| App Tracker | `/var/log/seclyzer/app_tracker.log` |

### Viewing Logs

**All logs:**
```bash
./scripts/dev logs
```

**Specific log:**
```bash
tail -f /var/log/seclyzer/keystroke_extractor.log
```

**JSON logs (parsed):**
```bash
./scripts/dev tail-json-logs
```

---

## 6. Troubleshooting

### Services Not Starting

**Check if already running:**
```bash
./scripts/dev status
```

**Stop all before restart:**
```bash
./scripts/dev stop
sleep 2
./scripts/dev start
```

### Database Connection Errors

**Check Redis:**
```bash
redis-cli ping
# Should return: PONG
```

**Check InfluxDB:**
```bash
curl http://localhost:8086/ping
# Should return HTTP 204
```

### No Data Being Collected

**Verify collectors are running:**
```bash
ps aux | grep collector
```

**Check for events in Redis:**
```bash
./scripts/dev debug-redis
# Then type/move mouse to see events
```

---

## 7. Quick Reference

### Daily Development Workflow
```bash
# Start the day
./scripts/dev start

# Check status
./scripts/dev status

# Run tests before committing
./scripts/dev test

# View logs while debugging
./scripts/dev logs

# Check data collection progress
./scripts/dev check-data

# Stop at end of day (optional)
./scripts/dev stop
```

### Before Committing Code
```bash
# Format code
./scripts/dev format

# Run linters
./scripts/dev lint

# Run full test suite
./scripts/dev test

# Clean up
./scripts/dev clean-pycache
```

---

## 8. Script Comparison

| Feature | `./scripts/seclyzer` | `./scripts/dev` |
|---------|----------------------|-----------------|
| **Target Audience** | End users | Developers |
| **Systemd Support** | ✅ Yes | ❌ No (manual only) |
| **Password Protection** | ✅ Yes | ❌ No |
| **Testing Tools** | ❌ No | ✅ Yes |
| **Debugging Tools** | ❌ No | ✅ Yes |
| **Auto-format Code** | ❌ No | ✅ Yes |
| **Show Metrics** | ✅ Basic | ✅ Detailed |
| **Log Parsing** | ❌ No | ✅ Yes (JSON) |

### When to Use Which?

**Use `./scripts/seclyzer`:**
- Production deployments
- When systemd services are installed
- For end-user operations
- When password protection is needed

**Use `./scripts/dev`:**
- Development and testing
- Debugging issues
- Running tests and linters
- Checking system metrics
- Monitoring logs

---

## 9. Advanced Usage

### Running Tests with Coverage
```bash
./scripts/dev test-coverage
# Opens htmlcov/index.html
```

### Monitoring Redis Events
```bash
# Terminal 1: Monitor events
./scripts/dev debug-redis

# Terminal 2: Type/move mouse
# You'll see events appear in Terminal 1
```

### Checking Configuration
```bash
./scripts/dev config
```
Shows:
- Environment variables (REDIS_*, INFLUX_*, SECLYZER_*)
- Config file locations
- Active configuration values

---

## 10. Tips & Best Practices

1. **Always use the dev script during development** - It provides better feedback and debugging tools

2. **Check status before starting** -Avoid duplicate processes:
   ```bash
   ./scripts/dev status
   ./scripts/dev start  # Only if needed
   ```

3. **Use test-coverage regularly** - Maintain 80%+ test coverage:
   ```bash
   ./scripts/dev test-coverage
   ```

4. **Monitor logs during debugging** - JSON logs are more informative:
   ```bash
   ./scripts/dev tail-json-logs
   ```

5. **Clean up before commits**:
   ```bash
   ./scripts/dev clean-pycache
   ./scripts/dev format
   ./scripts/dev lint
   ./scripts/dev test
   ```

---

## 11. Future Enhancements

Planned additions to control scripts:

- [ ] `./scripts/dev profile` - CPU/memory profiling
- [ ] `./scripts/dev benchmark` - Performance benchmarking
- [ ] `./scripts/dev validate-config` - Config file validation
- [ ] `./scripts/dev migrate` - Database migration tool
- [ ] `./scripts/dev doctor` - System diagnostic tool
- [ ] Integration test command
- [ ] Docker support

---

## Need Help?

```bash
# Show help for production script
./scripts/seclyzer help

# Show help for dev script
./scripts/dev help
```

For more information, see:
- `NEXT_AGENT_HANDOVER.md` - System architecture
- `CHANGELOG.md` - Recent changes
