# SECLYZER MASTER PROTOCOL - HANDOVER DOCUMENT

**Date:** December 2, 2025
**Status:** ✅ PHASE 3 COMPLETE - Model Training Implementation Ready
**Classification:** CONFIDENTIAL / LOCAL-ONLY

---

## 🎉 PHASE 3 COMPLETE: MODEL TRAINING IMPLEMENTATION (2025-12-02)

### What Was Implemented
- ✅ **Complete Training Pipeline**: All three model trainers implemented
  - `processing/models/train_keystroke.py` - Random Forest (140 features)
  - `processing/models/train_mouse.py` - One-Class SVM (38 features)
  - `processing/models/train_app_usage.py` - Markov Chain + Time Patterns
- ✅ **Training Orchestrator**: `scripts/train_models.py`
  - Data availability checking
  - Multi-model training support
  - Automatic versioning and metadata saving
- ✅ **Comprehensive Testing**: 49 tests passing
  - 12 tests for keystroke model
  - 17 tests for mouse model
  - 20 tests for app usage model
- ✅ **Performance Optimized**: Laptop-friendly configurations
  - Reduced tree count (50 vs 100) for Random Forest
  - Limited SVM cache (500MB)
  - Efficient data handling with Polars
  - No GPU required

### Current State
- ✅ **Extractors**: RUNNING (collecting data to InfluxDB)
- ✅ **Training Scripts**: READY (optimized and tested)
- ✅ **Tests**: 49/49 PASSING (model training tests)
- 📊 **Data Collection**: Active, ready to train when thresholds met
- 🎯 **Next Step**: Wait for sufficient data, then train models

### Training Requirements
- **Keystroke**: 500 min / 1000 recommended samples
- **Mouse**: 800 min / 1500 recommended samples  
- **App**: 50 min / 100 recommended transitions

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
   source ~/.seclyzer-venv/bin/activate
   export PYTHONPATH=$PYTHONPATH:.
   pytest tests/
   ```

**3. Check Data Readiness:**
   ```bash
   python scripts/train_models.py --check
   ```

**4. Train Models:** When sufficient data is available:
   ```bash
   # Train all models
   python scripts/train_models.py --all
   
   # Or train specific models
   python scripts/train_models.py --keystroke --mouse
   python scripts/train_models.py --app
   
   # With custom time window
   python scripts/train_models.py --all --days 14
   ```

**5. Start Inference:** (Phase 4 - Future work)
   - Inference engine not yet implemented
   - Will use trained ONNX models for real-time scoring

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

### Phase 3: Model Training (✅ COMPLETED - 2025-12-02)
-   **Goal:** Train ML models on collected data.
-   **Status:** Complete implementation with comprehensive testing.
-   **Models Implemented:**
    - Random Forest for keystroke dynamics (140 features)
    - One-Class SVM for mouse behavior (38 features)
    - Markov Chain for app usage patterns
-   **Features:**
    - Laptop-optimized performance
    - ONNX export for cross-platform inference
    - Automatic versioning and metadata storage
    - 49 passing unit tests
-   **Constraint:** User requested **NO ADAPTIVE TRAINING** (static models only).

---

## 4. FILE & ENVIRONMENT MANAGEMENT

### 1. Virtual Environment (CRITICAL)
-   **Path:** `~/.seclyzer-venv`
-   **Activation Rule:** You **MUST** activate the venv before running ANY Python script.
    ```bash
    source ~/.seclyzer-venv/bin/activate
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
-   **Source Code:** `~/SecLyzer/`
-   **Installed Location:** `/opt/seclyzer/`
-   **Data:** `/var/lib/seclyzer/`
-   **Logs:** `/var/log/seclyzer/`
-   **Config:** `/etc/seclyzer/`

---

## 5. IMPLEMENTATION ROADMAP (Your Orders)

### Phase 3: Model Training (✅ COMPLETED)
All training scripts implemented in `processing/models/`:

1.  **`train_keystroke.py` (Random Forest)** ✅
    -   **Input:** 140 features from InfluxDB.
    -   **Negative Samples:** Synthetic generation via noise injection and permutation.
    -   **Output:** `.pkl` + `.onnx` model.
    -   **Performance:** 50 trees, max depth 15, parallel processing.

2.  **`train_mouse.py` (One-Class SVM)** ✅
    -   **Input:** 38 features.
    -   **Method:** Anomaly detection (learns "normal" behavior).
    -   **Output:** `.pkl` + `.onnx` model with embedded scaler.
    -   **Performance:** RBF kernel, 500MB cache, automatic scaling.

3.  **`train_app_usage.py` (Statistical)** ✅
    -   **Method:** Markov Chain probabilities + Hourly usage heatmap.
    -   **Output:** `.json` model with transitions, time patterns, rankings.
    -   **Metrics:** Entropy, predictability score, transition density.

4.  **`scripts/train_models.py` (Orchestrator)** ✅
    -   Data availability checking.
    -   Multi-model training coordination.
    -   Comprehensive progress reporting.
    -   Automatic metadata storage.

### Phase 4: Inference Engine (Next Priority)
-   Build `inference/engine.py` using `onnxruntime`.
-   Real-time scoring of incoming feature vectors.
-   Weighted fusion of scores (Keystroke + Mouse + App).
-   Load trained ONNX models from `data/models/`.
-   Publish confidence scores to Redis.

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
    export PYTHONPATH=~/SecLyzer
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

## 📊 CURRENT PROJECT STATUS

### Completed Phases
- ✅ **Phase 1**: Data Collection (Rust collectors)
- ✅ **Phase 2**: Feature Extraction (Python extractors)  
- ✅ **Phase 3**: Model Training (All three models implemented)

### Testing Status
- ✅ **Total Tests**: 85+ passing
  - 36 tests (Phase 1-2)
  - 49 tests (Phase 3 - Model Training)
- ✅ **Test Coverage**: Comprehensive mocking and integration tests

### Next Steps
1. **Continue Data Collection**: Let system run to accumulate training data
2. **Train Models**: When thresholds met, use `python scripts/train_models.py --all`
3. **Implement Phase 4**: Inference engine with ONNX runtime
4. **Implement Phase 5**: System integration (PAM/GDM)

**PROJECT IS ON TRACK - PHASE 3 COMPLETE.**
