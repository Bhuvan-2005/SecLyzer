# SECLYZER MASTER PROTOCOL - HANDOVER DOCUMENT

**Date:** November 28, 2025 00:37 IST
**Status:** ⚠️ ROLLED BACK - Phase 3 Infrastructure Complete, Waiting for Data
**Classification:** CONFIDENTIAL / LOCAL-ONLY

---

## 🚨 CRITICAL: ROLLBACK STATUS (2025-11-28 00:33 IST)

### What Happened
- **Demo training attempted** with insufficient data (558 keystroke, 868 mouse vectors vs needed 10K/15K)
- Models trained but had poor quality (dimensions: 50 vs 140, 39 vs 38)
- **ROLLBACK EXECUTED**: Restored from backup `snapshot_20251127_235451`

### Current State
- ✅ **Extractors**: RUNNING (collecting data to InfluxDB)
- ❌ **Models**: NONE (all demo models deleted)
- ✅ **Phase 4 Code**: COMPLETE but inactive (no models to load)
- ✅ **Phase 7 Tests**: COMPLETE (36 unit tests passing)
- 📊 **Data Collection**: Active, needs 1-2 weeks

### What Was Deleted
- All demo-trained ONNX models (keystroke, mouse)
- Demo app models (v1.0.0_20251128_*)
- Database model records

### What Was Kept
- **Backup system** (`scripts/backup_system.sh`)
- Design/plans for an inference engine, trust scorer, live dashboard, and test suite (these components are **not** present in this repository snapshot and remain future work).

### Resume Instructions
**1. Maintain Data Collection:** Let extractors run for 1-2 weeks.

**⚠️ CRITICAL - After System Restart:**
Every time you reboot, you MUST manually start both collectors and extractors:
   ```bash
   cd ~/Documents/Projects/SecLyzer
   ./scripts/start_collectors.sh    # Start Rust input collectors
   ./scripts/start_extractors.sh    # Start Python feature extractors
   ```

**2. Run Tests:** Verify system integrity anytime:
   ```bash
   source /home/bhuvan/Documents/Projects/venv/bin/activate
   export PYTHONPATH=$PYTHONPATH:.
   pytest tests/
   ```
**3. Train Models:** When `scripts/check_training_readiness.py` says READY:
   ```bash
   python3 scripts/train_models.py --all --days 30
   ```
**4. Start Inference:** `sudo ./scripts/start_inference.sh`

**🔥 URGENT TODO:** Build auto-start system (Phase 5) to eliminate manual startup requirement!

---

## 1. MASTER DIRECTIVE & PHILOSOPHY
**SecLyzer** is a behavioral biometric authentication system designed for Linux environments.
-   **Core Mission:** Continuous, passive user verification to replace/augment static passwords.
-   **Privacy First:** All data processing is **LOCAL**. No cloud, no telemetry, no external API calls.
-   **Security:** Sensitive operations (stop/disable) require password verification.
-   **Performance:** Minimal resource footprint (Rust collectors, optimized Python extractors).

---

## 2. SYSTEM ARCHITECTURE (The Full Stack)

### Layer 1: Data Collection (Rust)
-   **`collectors/keyboard_collector`**: Uses `rdev`. Captures key press/release timings. Publishes to Redis.
-   **`collectors/mouse_collector`**: Captures movement/clicks. 50Hz sampling. Publishes to Redis.
-   **`collectors/app_monitor`**: Uses `x11rb`. Tracks active window focus. Publishes to Redis.
-   **Protocol:** Redis Pub/Sub channel `seclyzer:events`.

### Layer 2: Feature Extraction (Python)
-   **`processing/extractors/keystroke_extractor.py`**:
    -   140 features (Dwell time, Flight time, Digraphs, Rhythm).
    -   **NEW**: Publishes to Redis channel `seclyzer:features:keystroke`.
    -   Uses `polars` for sliding window processing.
-   **`processing/extractors/mouse_extractor.py`**:
    -   38 features (Velocity, Acceleration, Jerk, Curvature, Clicks).
    -   **NEW**: Publishes to Redis channel `seclyzer:features:mouse`.
    -   Uses `numpy` for vector math.
-   **`processing/extractors/app_tracker.py`**:
    -   Markov Chain transitions + Time-of-day patterns.
    -   **NEW**: Publishes to Redis channel `seclyzer:features:app`.
    -   **CRITICAL FIX:** Uses `datetime.utcfromtimestamp()` for InfluxDB compatibility.

### Layer 3: Storage
-   **InfluxDB (Time-Series)**: Stores feature vectors (`keystroke_features`, `mouse_features`, `app_transitions`).
    -   Retention: 30 days.
    -   Token: `/etc/seclyzer/influxdb_token` (chmod 600).
-   **SQLite (Metadata)**: Stores user profiles, model metadata, configuration.
    -   Path: `/var/lib/seclyzer/databases/seclyzer.db`.

---

## 3. PROJECT HISTORY & STATUS

### Phase 1: Infrastructure (Completed)
-   Built Rust collectors.
-   Set up Redis.
-   Created `install.sh` and `uninstall.sh`.
-   Implemented **Developer Mode** (bypass auth for testing).

### Phase 2: Processing & Control (Completed)
-   Built Python feature extractors.
-   Implemented InfluxDB/SQLite wrappers.
-   **Control System:** `seclyzer` script (start/stop/restart/status/resources).
-   **Security:** Added SHA-256 password protection for control operations.
-   **Readiness:** Created `scripts/check_training_readiness.py`.

### Phase 3: Model Training (STARTING NOW)
-   **Goal:** Train ML models on collected data.
-   **Constraint:** User requested **NO ADAPTIVE TRAINING** (static models only).
-   **Constraint:** User requested to **START IMMEDIATELY** (despite low data).

---

## 4. FILE & ENVIRONMENT MANAGEMENT

### 1. Virtual Environment (CRITICAL)
-   **Path:** `/home/bhuvan/Documents/Projects/venv`
-   **Activation Rule:** You **MUST** activate the venv before running ANY Python script.
    ```bash
    source /home/bhuvan/Documents/Projects/venv/bin/activate
    ```
-   **Dependency Management:**
    -   Core deps: `requirements.txt`
    -   ML deps: `requirements_ml.txt` (scikit-learn, pandas, etc.)
    -   **Action:** If you add new imports, update the relevant requirements file immediately.

### 2. Installation System (`install.sh`)
-   **Role:** The single source of truth for deployment.
-   **Responsibility:** If you add new files (e.g., training scripts, models), you **MUST update `install.sh`** to ensure they are:
    1.  Copied to `/opt/seclyzer/`
    2.  Permissions set correctly
    3.  Included in the uninstaller generation logic
-   **Current Status (ALREADY RUN):**
    -   `install.sh`: **EXECUTED**. System is installed at `/opt/seclyzer`.
    -   `scripts/setup_redis.sh`: **EXECUTED**. Redis is running (port 6379).
    -   `scripts/setup_influxdb.sh`: **EXECUTED**. InfluxDB is running (port 8086).
    -   `scripts/setup_sqlite.sh`: **EXECUTED**. DB exists at `/var/lib/seclyzer/databases/seclyzer.db`.
    -   **Action:** Do NOT re-run these setup scripts unless you are deliberately resetting the environment.

### 3. Key File Locations
-   **Source Code:** `/home/bhuvan/Documents/Projects/SecLyzer/`
-   **Installed Location:** `/opt/seclyzer/`
-   **Data:** `/var/lib/seclyzer/`
-   **Logs:** `/var/log/seclyzer/`
-   **Config:** `/etc/seclyzer/`

---

## 5. IMPLEMENTATION ROADMAP (Your Orders)

### Phase 3: Model Training (Immediate Task)
You must implement the following scripts in `training/`:

1.  **`train_keystroke.py` (Random Forest)**
    -   **Input:** 140 features from InfluxDB.
    -   **Negative Samples:** Download public datasets (CMU/Clarkson) via `scripts/download_negative_samples.sh`.
    -   **Output:** `.onnx` model.

2.  **`train_mouse.py` (One-Class SVM)**
    -   **Input:** 38 features.
    -   **Method:** Anomaly detection (learns "normal" behavior).
    -   **Output:** `.onnx` model.

3.  **`train_app_usage.py` (Statistical)**
    -   **Method:** Markov Chain probabilities + Hourly usage heatmap.
    -   **Output:** `.json` model.

4.  **`evaluate_models.py`**
    -   Calculate FAR/FRR/EER.
    -   Generate performance report.

### Phase 4: Inference Engine (Future)
-   Build `inference/engine.py` using `onnxruntime`.
-   Real-time scoring of incoming feature vectors.
-   Weighted fusion of scores (Keystroke + Mouse + App).

### Phase 5: System Integration (Future)
-   Integrate with Linux PAM or GDM to lock screen on high anomaly score.

---

## 5. OPERATIONAL PROTOCOLS

### 1. Integrity & Confidentiality
-   **NEVER** upload user data to cloud.
-   **ALWAYS** respect file permissions (`chmod 600` for secrets).
-   **ALWAYS** update `CHANGELOG.md` after significant changes.

### 2. Running & Debugging
-   **Control:** Use `seclyzer` command (e.g., `seclyzer restart`).
-   **Logs:** Check `/var/log/seclyzer/*.log`.
-   **Manual Run:**
    ```bash
    export PYTHONPATH=/home/bhuvan/Documents/Projects/SecLyzer
    python3 path/to/script.py
    ```

### 3. Critical Technical Context (DO NOT IGNORE)
-   **UTC Timestamps:** InfluxDB writes MUST use UTC. `app_tracker.py` was fixed to use `datetime.utcfromtimestamp()`. Do not regress this.
-   **Python Imports:** The venv has a conflicting `storage` package. Always set `PYTHONPATH` to the project root to force using our local `storage/` module.
-   **X11 Dependency:** Collectors require `DISPLAY=:0`. This is handled in `start_extractors.sh`.

---

## 6. USER RULES & PREFERENCES
1.  **No Adaptive Training:** Do not build auto-retraining logic. Models are static.
2.  **Start Immediately:** Do not wait for "optimal" data volume. Build the training infrastructure NOW.
3.  **Hybrid Approach:** (Cancelled/Reverted). Stick to the original plan.

**EXECUTE PHASE 3 IMMEDIATELY.**
