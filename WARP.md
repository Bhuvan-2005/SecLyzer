# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development environment & core commands

### Warp quick-start (for agents & humans)
- From repo root:
  - **Start everything for a dev session:** `./scripts/dev check-health && ./scripts/dev start`
  - **Inspect status:** `./scripts/dev status`
  - **Watch logs while you experiment:** `./scripts/dev logs` or `./scripts/dev tail-json-logs`
  - **Run tests before changes land:** `./scripts/dev test` (or `./scripts/dev test-coverage`)
  - **Keep style consistent:** `./scripts/dev format` then `./scripts/dev lint`

### Python environment
- Virtualenv is expected at `~/.seclyzer-venv`.
- Always activate it before running Python tooling for this project:
  ```bash
  source ~/.seclyzer-venv/bin/activate
  export PYTHONPATH=~/SecLyzer:$PYTHONPATH
  ```

### High-level control scripts
- **Developer console (preferred for local work):** `./scripts/dev`
  - Service lifecycle: `./scripts/dev start`, `./scripts/dev stop`, `./scripts/dev restart`, `./scripts/dev status`, `./scripts/dev logs`
  - Health & env: `./scripts/dev check-health`, `./scripts/dev config`, `./scripts/dev env`, `./scripts/dev show-metrics`
- **Production-style control script:** `./scripts/seclyzer`
  - Typical usage: `./scripts/seclyzer start`, `./scripts/seclyzer status`, `./scripts/seclyzer resources`
  - Auth on/off: `./scripts/seclyzer disable` (keep collectors running, disable auth), `./scripts/seclyzer enable`
  - Auto-start (when systemd units are installed): `./scripts/seclyzer autostart`, `./scripts/seclyzer no-autostart`

### Building Rust collectors
- All Rust collectors live under `collectors/`.
- To build every collector in one step:
  ```bash
  ./scripts/build_collectors.sh
  ```
- Resulting binaries:
  - `collectors/keyboard_collector/target/release/keyboard_collector`
  - `collectors/mouse_collector/target/release/mouse_collector`
  - `collectors/app_monitor/target/release/app_monitor`

### Running services for development
- Recommended dev workflow (from repo root):
  ```bash
  ./scripts/dev check-health     # verify Python venv, Redis, InfluxDB, Rust
  ./scripts/dev start            # start collectors + Python extractors
  ./scripts/dev status           # confirm everything is running
  ./scripts/dev logs             # tail all logs when debugging
  ```
- Manual fallback (without the dev script), if ever needed:
  - Collectors (after building via `build_collectors.sh`):
    ```bash
    # from repo root
    sudo collectors/keyboard_collector/target/release/keyboard_collector
    sudo collectors/mouse_collector/target/release/mouse_collector
    collectors/app_monitor/target/release/app_monitor
    ```
  - Python extractors (with venv active and `PYTHONPATH` set):
    ```bash
    python3 processing/extractors/keystroke_extractor.py
    python3 processing/extractors/mouse_extractor.py
    python3 processing/extractors/app_tracker.py
    ```

### Testing & coverage
- Project uses `pytest` with `pytest.ini` pointing at the `tests/` package.
- Common commands (preferred via dev script):
  ```bash
  ./scripts/dev test           # run full test suite
  ./scripts/dev test-coverage  # run tests with coverage + HTML report
  ```
- Direct `pytest` usage (with venv active and `PYTHONPATH` set):
  - Full suite:
    ```bash
    pytest tests/
    ```
  - Single test file:
    ```bash
    pytest tests/extractors/test_keystroke_extractor.py
    ```
  - Single test function:
    ```bash
    pytest tests/extractors/test_keystroke_extractor.py::test_some_behavior
    ```

### Linting & formatting
- Run via the dev script (which wires up `black`, `isort`, `flake8`, `mypy`):
  ```bash
  ./scripts/dev lint     # style + basic type checks
  ./scripts/dev format   # auto-format (black + isort)
  ```

### Data, logs, and backups
- Log directory: `/var/log/seclyzer` (used by dev + control scripts).
- Quick log inspection:
  ```bash
  ./scripts/dev logs
  ./scripts/dev tail-json-logs
  ```
- System backup helper (wraps `scripts/backup_system.sh` if present):
  ```bash
  ./scripts/dev backup
  ```

### Rust extractor workspace (test_environment)
- There is a separate Rust workspace that mirrors the Python extractors for performance testing:
  - Root: `test_environment/extractors_rs/`
  - Members: `common`, `keystroke_extractor`, `mouse_extractor`, `app_tracker`
- Typical commands (from `test_environment/extractors_rs/`):
  ```bash
  cargo build --release                       # build all workspace members
  cargo build --release -p keystroke_extractor
  cargo run --release -p keystroke_extractor  # test keystroke extractor against Redis/Influx
  ```

## High-level architecture

### End-to-end pipeline
- The system implements a behavioral-auth pipeline:
  1. **Collectors (Rust, `collectors/`)** capture raw keyboard, mouse, and app-focus events from the OS.
  2. **Message transport (Redis)** carries normalized event messages on channels such as `seclyzer:events`.
  3. **Python extractors (`processing/extractors/`)** consume event streams and compute feature vectors per modality.
  4. **Time-series & metadata storage (`storage/`, external DBs)** persist feature vectors (InfluxDB) and metadata/models (SQLite).
  5. **Model training & inference layers** are designed around these features (training/inference scripts are partially planned and not all are present in this snapshot).
  6. **Control scripts (`scripts/seclyzer`, `scripts/dev`)** orchestrate processes and, in later phases, will manage auth on/off and auto-start.

### Collectors (Rust, `collectors/`)
- Three independent Rust binaries:
  - `keyboard_collector`: captures key press/release events with timestamps and publishes to Redis.
  - `mouse_collector`: captures mouse movement, clicks, and scroll events.
  - `app_monitor`: tracks the currently focused application/window on X11.
- Each collector is responsible only for high-frequency, low-latency event capture and normalization; no heavy processing or ML occurs here.

### Python feature extraction layer (`processing/extractors/`)
- Three main extractors correspond 1:1 with collectors:
  - `keystroke_extractor.py`: computes ~140-dimensional keystroke dynamics features (dwell times, flight times, digraph statistics, rhythm metrics, error patterns) from keyboard events.
  - `mouse_extractor.py`: computes ~38 mouse features (velocity, acceleration, jerk, curvature, click/drag patterns).
  - `app_tracker.py`: builds app-usage features (transitions, dwell time per app, time-of-day patterns) and writes to InfluxDB.
- All extractors:
  - Subscribe to Redis event channels.
  - Maintain sliding windows (e.g., ~30 seconds) over raw events.
  - Emit structured feature vectors both to Redis feature channels and to the time-series database.

### Storage layer (`storage/` and external DBs)
- **Time-series features (InfluxDB):** encapsulated behind `storage/timeseries.py`.
  - Measurements like `keystroke_features`, `mouse_features`, and app-usage series are written here.
  - Training scripts and diagnostics query InfluxDB via this module.
- **Metadata & models (SQLite):** encapsulated behind `storage/database.py`.
  - Intended schema includes user profile, model metadata, configuration, and audit logs (see `ARCHITECTURE.md`).
- The Python code accesses databases exclusively through these abstractions; avoid adding direct InfluxDB/SQLite code in random modules.

### Common Python utilities (`common/`)
- `common/config.py`: configuration loading and environment handling (project-level config, external `/etc/seclyzer` YAML files, etc.).
- `common/logger.py`: unified, JSON-capable logging utilities used across collectors/extractors and higher-level services.
- `common/developer_mode.py`: developer-mode toggling logic (magic file, env var, etc.), checked by decision logic to bypass authentication when active.
- `common/paths.py`, `common/retry.py`, `common/validators.py`: shared helpers for consistent paths, retry behavior, and input validation.
- Tests in `tests/common/` cover these foundational utilities; changes here tend to have impact across the entire codebase.

### Control and orchestration (`scripts/` + systemd units)
- `scripts/dev`: developer console that knows how to:
  - Start/stop collectors and extractors (`start`, `stop`, `restart`).
  - Run tests, linters, and formatters.
  - Inspect health, metrics, and configuration.
  - Interact with Redis/Influx (debug commands).
- `scripts/seclyzer`: user-facing control script focused on production usage:
  - Integrates with systemd units under `systemd/` (e.g., `seclyzer-keyboard@.service`).
  - Knows how to enable/disable auto-start and toggle authentication (via developer mode) without necessarily stopping collectors.
- `install.sh` and docs in `docs/INSTALLATION.md` define the canonical installation layout under `/opt/seclyzer`, `/var/lib/seclyzer`, `/var/log/seclyzer`, `/etc/seclyzer`.

### Tests (`tests/`)
- Organized by domain, mirroring the main packages:
  - `tests/common/`: core configuration/logging/retry/validator behavior.
  - `tests/extractors/`: keystroke, mouse, and app-tracker feature extraction.
  - `tests/storage/`: database and time-series wrappers.
  - `tests/integration/`: end-to-end/CLI-level checks (e.g., smoke tests for scripts and pipelines).
- Use this structure as guidance when adding tests for new modules (place them in the matching subpackage under `tests/`).

### Rust test environment (`test_environment/extractors_rs/`)
- A separate Rust workspace that mirrors the Python extractors:
  - `common/`: shared Redis, InfluxDB, config, and logging utilities.
  - `keystroke_extractor/`, `mouse_extractor/`, `app_tracker/`: Rust ports of the Python extractors, designed for lower CPU/memory usage while preserving feature semantics.
- This workspace is meant for performance validation and future migration; keep feature definitions in sync with the Python versions when updating either side.

## Project-specific constraints & expectations

- All behavioral and model data is intended to stay **local** (no cloud services, telemetry, or remote APIs); avoid introducing outbound network calls beyond the configured local Redis/InfluxDB endpoints.
- Model training and retraining logic is designed to be **explicit and operator-controlled**, not adaptive or continuously self-updating; any new training/inference code should follow the patterns and constraints outlined in `NEXT_AGENT_HANDOVER.md`.
- `install.sh` and the control scripts are treated as the source of truth for how the system is run in practice; when adding new long-lived services, scripts, or model artifacts that must be present on a deployed system, ensure they are wired through these entry points rather than introducing ad-hoc launch paths.
- For operational behavior and day-to-day usage patterns, refer to:
  - `README.md` (high-level overview and common workflows),
  - `docs/CONTROL_SCRIPTS.md` (detailed behavior of `./scripts/dev` and `./scripts/seclyzer`),
  - `NEXT_AGENT_HANDOVER.md` (current phase, rollback notes, and roadmap).

### Warp-specific notes & local-only files
- This `WARP.md` is meant to be committed and shared; keep it free of secrets.
- If you want **profile-independent, local-only Warp notes** (for example, prompts or scratch instructions you do not want on GitHub), store them under a local directory like `.warp-local/` in this repo.
- Files in `.warp-local/` are gitignored (see `.gitignore`), so they will:
  - Survive Warp profile changes on this machine (they are regular files in the repo directory).
  - Not be pushed to GitHub.
- When something in a Warp session feels important long-term, copy the stable, non-sensitive parts into this `WARP.md` so future agents and clones of the repo can rely on it.
