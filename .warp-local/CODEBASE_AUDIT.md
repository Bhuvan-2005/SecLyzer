# SecLyzer Complete Codebase Audit
**Last Audited:** 2025-12-01  
**Profile-Independent:** YES (stored in `.warp-local/`, survives all profile changes)  
**Status:** Phase 3 - Data Collection & Training Infrastructure  

---

## CRITICAL SETUP NOTES
- **Python venv location:** `/home/bhuvan/Documents/Projects/venv`
- **Always activate before running Python:** `source /home/bhuvan/Documents/Projects/venv/bin/activate`
- **Set PYTHONPATH:** `export PYTHONPATH=/home/bhuvan/Documents/Projects/SecLyzer:$PYTHONPATH`
- **OS:** Ubuntu Linux
- **Shell:** Bash 5.2.21

---

## PROJECT OVERVIEW
SecLyzer is a **behavioral biometric authentication system** that monitors keyboard, mouse, and application usage patterns for continuous user verification. It's designed to stay completely local (no cloud/telemetry).

### Core Architecture: 6-Layer Pipeline
1. **Collectors (Rust)** → 2. **Redis message queue** → 3. **Extractors (Python)** → 4. **Storage (InfluxDB/SQLite)** → 5. **ML Models** → 6. **Inference Engine** (planned)

---

## COMPLETE FILE INVENTORY

### ROOT LEVEL
| File | Purpose |
|------|---------|
| `README.md` | High-level overview, quick start guide |
| `WARP.md` | Warp agent guidance (shared, profile-independent) |
| `.warp-local/` | Local-only context (this file) - NOT in git |
| `ARCHITECTURE.md` | Detailed system design with diagrams |
| `NEXT_AGENT_HANDOVER.md` | Current phase status, rollback notes, roadmap |
| `CHANGELOG.md` | Version history and changes |
| `install.sh` | System installer (canonical deployment source) |
| `pytest.ini` | PyTest configuration |
| `requirements_ml.txt` | ML/data dependencies (scikit-learn, pandas, etc.) |
| `.gitignore` | Git exclusions (includes `.warp-local/`) |
| `.env.example` | Example environment variables |

### PYTHON MODULES

#### `common/` - Shared Utilities
- **`config.py`** (137 lines)
  - Singleton config manager
  - Loads from YAML or environment variables
  - Methods: `get()` (dot notation), `get_redis_config()`, `get_influx_config()`
  - Defaults: localhost Redis/InfluxDB, org=`seclyzer`, bucket=`behavioral_data`

- **`logger.py`** (124 lines)
  - JSON-formatted structured logging
  - `JSONFormatter`: outputs ISO timestamps, correlation IDs, log level
  - `CorrelationLogger`: adds request tracing IDs to logs
  - `get_logger()`: primary function to use
  - Log level from `SECLYZER_LOG_LEVEL` env var

- **`developer_mode.py`** (295 lines)
  - **SECURITY BYPASS** for development only
  - 4 activation methods:
    1. Magic file (`/tmp/.seclyzer_dev_mode`)
    2. Environment variable (`SECLYZER_DEV_MODE=1`)
    3. Key sequence (Ctrl+Shift+F12)
    4. Password override (SHA256 hash)
  - Auto-disables after 24 hours (configurable)
  - Tags collected data with `dev_mode: true` (excluded from training)
  - Logs all activations to `/var/log/seclyzer/dev_mode.log`

- **`validators.py`** (97 lines)
  - Pydantic models for event validation
  - `KeystrokeEvent`: type, event (press/release), key, ts (microseconds), scan_code
  - `MouseEvent`: type, event (move/press/release/scroll), x, y, button, scroll_delta
  - `AppEvent`: type, app_name, ts
  - All validate timestamp bounds (±1 hour from current time)
  - `validate_event()`: main validation function

- **`paths.py`** (144 lines)
  - XDG Base Directory compliance
  - Functions: `get_data_dir()`, `get_config_dir()`, `get_cache_dir()`, `get_log_dir()`
  - System install: `/var/lib/`, `/etc/`, `/var/log/`
  - User install: `~/.local/share/`, `~/.config/`, `~/.cache/`
  - Auto-creates directories on import

- **`retry.py`** (71 lines)
  - `@retry_with_backoff()` decorator
  - Exponential backoff: max_attempts, initial_delay, backoff_factor
  - Used for resilient database/network operations

- **`__init__.py`** (empty)

#### `storage/` - Database Abstraction
- **`database.py`** (200 lines)
  - SQLite wrapper for metadata/models
  - Tables: `user_profile`, `models`, `config`, `audit_log`
  - Methods:
    - User: `get_user()`, `update_user_status()`
    - Models: `save_model_metadata()`, `get_latest_model()`, `list_models()`
    - Config: `get_config()`, `set_config()`
    - Audit: `log_event()`, `get_recent_events()`, `get_events_by_type()`
  - Datetime adapters for Python 3.12+ compatibility
  - Context manager support (`with` syntax)

- **`timeseries.py`** (236 lines)
  - InfluxDB client wrapper for time-series features
  - Measurements: `keystroke_features`, `mouse_features`, `app_transitions`, `confidence_scores`
  - Write functions: `write_keystroke_features()`, `write_mouse_features()`, `write_app_transition()`, `write_confidence_score()`
  - Query functions: `query_keystroke_features()`, `query_mouse_features()`, `query_recent_features()`, `get_latest_score()`
  - Retry decorator on all writes
  - Token loaded from `/etc/seclyzer/influxdb_token` or env var
  - `delete_old_data()`: cleanup function for retention policy

- **`__init__.py`** (empty)

#### `processing/extractors/` - Feature Extraction
- **`keystroke_extractor.py`** (323 lines)
  - **140 features** computed from keyboard events:
    - Dwell times (8): mean, std, min, max, median, Q25, Q75, range
    - Flight times (8): mean, std, min, max, median, Q25, Q75, range
    - Digraphs (20): top 20 key-pair timings
    - Error patterns (4): backspace frequency, count, correction rate, clean ratio
    - Rhythm (8): consistency, burst/pause freq, typing speed, stability
    - Metadata (2): dev_mode flag, total_keys
  - Sliding window: 30 seconds (configurable)
  - Update interval: 5 seconds
  - Uses Polars DataFrame for fast processing
  - Validates events with Pydantic before processing
  - Publishes to Redis channel: `seclyzer:features:keystroke`
  - Writes to InfluxDB measurement: `keystroke_features`

- **`mouse_extractor.py`** (309 lines)
  - **38 features** from mouse events:
    - Movement (20): velocity stats, acceleration, curvature, jerk, distance, idle time, efficiency
    - Clicks (10): click duration, left/right/middle counts, double-click rate, click frequency
    - Scrolls (8): scroll magnitude, direction ratios, scroll frequency and intervals
  - Same 30s window, 5s update interval
  - High buffer size: 50,000 events (mouse generates many events)
  - Velocity calculation with outlier removal
  - Curvature = 1 - (straight_distance / total_distance)
  - Publishes to: `seclyzer:features:mouse`
  - Writes to: `mouse_features` measurement

- **`app_tracker.py`** (293 lines)
  - Monitors application usage patterns
  - Tracks: transition matrix, time-of-day preferences, usage statistics
  - Methods:
    - `_calculate_transition_matrix()`: Markov chain transitions
    - `_calculate_time_preferences()`: hourly usage heatmap
    - `_calculate_usage_stats()`: top apps, avg durations
    - `get_transition_probability()`: P(from_app → to_app)
    - `get_time_probability()`: P(app at hour)
    - `calculate_anomaly_score()`: detect unusual app sequences
  - Update interval: 60 seconds
  - Publishes to: `seclyzer:features:app`
  - Writes to: `app_transitions` measurement

- **`__init__.py`** (empty)

### RUST COLLECTORS (`collectors/`)

#### `keyboard_collector/`
- **`Cargo.toml`**: rdev, redis, serde, chrono
- **`src/main.rs`** (63 lines)
  - Uses `rdev` crate for global keyboard listening
  - Captures: KeyPress, KeyRelease events
  - JSON event: `{type, ts (μs), key, event}`
  - Publishes to Redis channel: `seclyzer:events`
  - Requires root to access `/dev/input`

#### `mouse_collector/`
- **`Cargo.toml`**: rdev, redis, serde, chrono
- **`src/main.rs`** (97 lines)
  - Captures: MouseMove, ButtonPress, ButtonRelease, Wheel events
  - JSON event: `{type, ts (μs), x, y, event, button, scroll_delta}`
  - Publishes to: `seclyzer:events`
  - Requires root access

#### `app_monitor/`
- **`Cargo.toml`**: sysinfo, redis, serde, chrono, **x11rb** (X11-specific)
- **`src/main.rs`** (126 lines)
  - X11-based window monitoring (Linux only)
  - Polls active window every 500ms
  - Extracts: app_name, window_class from `WM_CLASS` property
  - Only publishes on app change
  - JSON event: `{type, ts (μs), app_name, window_class, event}`
  - Requires X11 (NOT Wayland compatible)
  - Uses `_NET_ACTIVE_WINDOW` atom

### RUST TEST ENVIRONMENT (`test_environment/extractors_rs/`)
Performance-optimized Rust ports of Python extractors.

#### `common/`
- Shared Redis, InfluxDB, config utilities
- `redis_client.rs`: connection pooling
- `influx_client.rs`: async InfluxDB writes
- `models.rs`: data structures
- `config.rs`: environment-based config
- `logger.rs`: structured logging

#### `keystroke_extractor/`
- Mirrors Python version (140 features)
- Async/await with Tokio
- Same feature definitions for parity
- Workspace member dependency on `common`

#### `mouse_extractor/`, `app_tracker/`
- Similar structure to keystroke
- Ready for implementation

### CONTROL SCRIPTS (`scripts/`)

#### `./scripts/dev` (630 lines)
Developer management console with 30+ commands:
- **Service**: start, stop, restart, status, logs
- **Testing**: test, test-coverage, lint, format, check-health
- **Data**: check-data, train, export-data, backup, backup-git
- **Debugging**: debug-redis, debug-influx, show-metrics, tail-json-logs
- **Config**: config, env, version
- **Cleanup**: clean-logs, clean-pycache, reset-data

#### `./scripts/seclyzer` (420 lines)
Production control script:
- **Commands**: start, disable, enable, stop-all, restart, status, resources
- **Auto-start**: autostart, no-autostart
- **Security**: Password verification for sensitive commands
- **Systemd integration**: Auto-detects systemd services

#### `./scripts/build_collectors.sh` (39 lines)
Builds all Rust collectors:
- Compiles: keyboard_collector, mouse_collector, app_monitor
- Outputs: `collectors/*/target/release/*`

#### `./scripts/start_collectors.sh`
Starts Rust collectors with proper permissions

#### `./scripts/start_extractors.sh`
Starts Python extractors with venv activation

#### `./scripts/setup_redis.sh`, `setup_influxdb.sh`, `setup_sqlite.sh`
Database initialization scripts

### SYSTEMD UNITS (`systemd/`)
- `seclyzer-keyboard@.service`: Keyboard collector
- `seclyzer-mouse@.service`: Mouse collector
- `seclyzer-app@.service`: App monitor
- `seclyzer-extractors@.service`: Python extractors

### TESTS (`tests/`)
32 tests organized by domain:

#### `common/`
- `test_config.py`: Config loading, defaults, env overrides
- `test_logger.py`: JSON formatting, correlation IDs
- `test_developer_mode.py`: Dev mode activation, data tagging
- `test_retry.py`: Exponential backoff
- `test_validators.py`: Event validation schemas

#### `extractors/`
- `test_keystroke_extractor.py`: Feature extraction, dwell/flight times
- `test_mouse_extractor.py`: Movement features, click detection
- `test_app_tracker.py`: Transition matrix, anomaly scoring

#### `storage/`
- `test_database.py`: SQLite CRUD operations
- `test_timeseries.py`: InfluxDB writes/queries

#### `integration/`
- `test_cli_smoke.py`: End-to-end script execution
- `test_feature_pipeline.py`: Full data flow

#### `conftest.py`
PyTest fixtures and configuration

### CONFIGURATION

#### `config/seclyzer.yml`
Main config (YAML format):
- Database endpoints (Redis, InfluxDB, SQLite)
- Extractor settings (window_seconds, update_interval, enabled flags)
- Model thresholds and weights
- Trust scorer parameters
- Logging level

#### `config/dev_mode.yml`
Developer mode config:
- Enable/disable dev mode
- Activation methods (magic file, env var, key sequence, password)
- Auto-disable timeout (hours)
- Audit logging settings

#### `.env.example`
Environment variable template:
- REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
- INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET
- SECLYZER_DEV_MODE, SECLYZER_LOG_LEVEL
- PYTHONPATH

### DOCUMENTATION

#### `docs/CONTROL_SCRIPTS.md`
Complete reference for `./scripts/dev` and `./scripts/seclyzer`

#### `docs/DEVELOPER_MODE.md`
Security bypass modes, activation methods, example usage

#### `docs/DEV_MODE_DATA.md`
How dev mode affects data collection and training

#### `docs/INSTALLATION.md`
Installation steps, customization options, troubleshooting

#### `docs/PHASE1_TESTING.md`, `PHASE2_TESTING.md`
Phase-specific testing procedures

---

## KEY DATA FLOWS

### Keystroke Event Pipeline
```
Keyboard Hardware
  ↓ (rdev)
keyboard_collector (Rust)
  ↓ (JSON publish)
Redis: seclyzer:events channel
  ↓ (subscribe + parse)
keystroke_extractor.py
  ↓ (Polars DataFrame processing)
140-feature vector (dwell, flight, digraph, error, rhythm)
  ↓ (write + publish)
InfluxDB (keystroke_features measurement)
Redis (seclyzer:features:keystroke)
```

### App Usage Pipeline
```
X11 Window Manager
  ↓ (x11rb query)
app_monitor (Rust)
  ↓ (on app change)
Redis: seclyzer:events
  ↓
app_tracker.py
  ↓ (transition matrix, time patterns)
Transition: {from_app, to_app, duration_ms}
  ↓
InfluxDB (app_transitions measurement)
Config DB (app_patterns)
Redis (seclyzer:features:app)
```

---

## CRITICAL CONSTRAINTS & DESIGN DECISIONS

### 1. **Local-Only Processing**
- NO cloud APIs, NO telemetry, NO remote calls
- All data stays on `/var/lib/seclyzer/`
- No network calls except to local Redis/InfluxDB

### 2. **Static Models (Non-Adaptive)**
- Models are trained once on historical data
- NO automatic retraining
- NO self-updating weights
- Explicit user action required to retrain

### 3. **Developer Mode Isolation**
- Dev mode data tagged with `dev_mode: true`
- Automatically excluded from training
- Can be included as negative samples (adversarial training)
- Logged to audit file for compliance

### 4. **Timestamp Precision**
- All events: **microseconds since UNIX epoch** (u128)
- Feature calculations: converted to milliseconds/seconds
- Database writes: UTC timezone
- Time validation: ±1 hour bounds to catch clock skew

### 5. **Redis as Message Bus**
- NOT for persistence
- Channels: `seclyzer:events`, `seclyzer:features:*`
- Pub/Sub pattern for loose coupling
- Event format: JSON with `type` field

### 6. **Feature Extraction Windows**
- Keystroke: 30-second sliding window, update every 5 seconds
- Mouse: 30-second sliding window, update every 5 seconds
- App: tracks transitions continuously, patterns updated every 60 seconds
- Minimum event thresholds to avoid spurious features

### 7. **Database Schema Separation**
- **InfluxDB**: Time-series features (measurements) + high-cardinality data
- **SQLite**: Metadata (models, users, config) + low-cardinality data
- Access ONLY through abstraction layer (`storage.py` modules)
- Never direct SQL/Flux queries in extractors

---

## INSTALLATION PATHS (Production)
- **Binaries**: `/opt/seclyzer/bin/`
- **Data**: `/var/lib/seclyzer/` (models, databases)
- **Logs**: `/var/log/seclyzer/`
- **Config**: `/etc/seclyzer/`
- **Systemd**: `/etc/systemd/system/seclyzer-*.service`

---

## KEY METRICS & DIMENSIONS

### Keystroke Features (140 total)
- Dwell times: 8 (mean, std, min, max, median, Q25, Q75, range)
- Flight times: 8 (same stats)
- Digraphs: 20 (mean timing for top 20 key-pairs)
- Errors: 4 (backspace freq/count, correction rate, clean ratio)
- Rhythm: 8 (consistency, burst/pause freq, typing speed, stability)
- Metadata: 2 (dev_mode, total_keys)

### Mouse Features (38 total)
- Movement: 20 (velocity, acceleration, curvature, jerk, distance, idle, efficiency)
- Clicks: 10 (duration, left/right/middle, double-click, frequency)
- Scrolls: 8 (magnitude, direction, frequency, intervals)

### App Tracking
- Transition matrix: P(from_app → to_app)
- Time patterns: P(app | hour_of_day)
- Usage stats: top apps, avg durations, anomaly scores

---

## TESTING COVERAGE
- **32 tests** across common, extractors, storage, integration (all passing ✅)
- **pytest.ini** configured for `tests/` package
- **Coverage tools**: pytest-cov (HTML reports available via `./scripts/dev test-coverage`)
- **Lint commands** exposed via `./scripts/dev lint` (black, isort, flake8, mypy; tools must be installed in the venv)
- **Verification:** All tests pass with 0 failures, 1 external warning (dateutil, outside our control)

### Running Tests
```bash
source /home/bhuvan/Documents/Projects/venv/bin/activate
export PYTHONPATH=/home/bhuvan/Documents/Projects/SecLyzer:$PYTHONPATH
./scripts/dev test              # Run all tests
./scripts/dev test-coverage     # With HTML report
pytest tests/extractors/test_keystroke_extractor.py  # Specific file
```

---

## COMMON ISSUES & SOLUTIONS

### "connection refused" (Redis)
- Check: `redis-cli ping` → should return PONG
- Start: `redis-server` or `sudo systemctl start redis-server`

### "Failed to connect to InfluxDB"
- Check: `curl http://localhost:8086/ping` → should return 204
- Verify token in `/etc/seclyzer/influxdb_token`

### "X11 connection failed" (App monitor)
- Requires X11, not Wayland
- Check: `echo $XDG_SESSION_TYPE` → should be "x11"
- Fix: Logout → select "Ubuntu on Xorg" at login

### "Cannot find module" (Python imports)
- Set `PYTHONPATH=/home/bhuvan/Documents/Projects/SecLyzer:$PYTHONPATH`
- Activate venv: `source /home/bhuvan/Documents/Projects/venv/bin/activate`

### "dev mode not working"
- Check: `ls -l /tmp/.seclyzer_dev_mode` (magic file method)
- Check: `cat /var/log/seclyzer/dev_mode.log` (audit log)
- Verify: Config at `/etc/seclyzer/dev_mode.yml` has `enabled: true`

---

## PHASE ROADMAP

### ✅ Phase 1: Data Collection (COMPLETE)
- Rust collectors (keyboard, mouse, app)
- Redis message bus
- Event validation

### ✅ Phase 2: Feature Extraction (COMPLETE)
- Python extractors for all modalities
- InfluxDB storage
- SQLite metadata DB

### ✅ Phase 3: Model Training Infrastructure (IN PROGRESS)
- Training scripts (partially planned)
- Data readiness checks
- Demo models (currently rolled back)

### ⏳ Phase 4: Inference Engine (FUTURE)
- ONNX runtime
- Real-time scoring
- Confidence fusion

### ⏳ Phase 5: System Integration (FUTURE)
- PAM/GDM integration
- Screen locking on anomaly
- Systemd auto-start

---

## FOR NEXT WARP AGENT (PROFILE SWITCHES)
This document is stored in `.warp-local/CODEBASE_AUDIT.md` and survives all profile changes because:
1. It's a local file in the repo directory (not in Warp cloud)
2. `.warp-local/` is in `.gitignore` (not committed to GitHub)
3. It persists between Warp profile switches on the same machine

**Actions for next agent:**
1. Read this file first
2. Verify all paths are correct (`/home/bhuvan/` prefix)
3. Check `.warp-local/` directory for any session notes
4. Follow WARP.md for development workflow
5. Use `./scripts/dev` for all common tasks
