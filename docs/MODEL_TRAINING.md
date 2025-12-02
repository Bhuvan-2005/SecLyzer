# SecLyzer - Model Training Guide

**Version:** 1.0.0  
**Last Updated:** December 2, 2025

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Model Details](#model-details)
5. [Training Process](#training-process)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)

---

## Overview

SecLyzer trains three machine learning models to learn your unique behavioral patterns:

| Model | Algorithm | Features | Purpose |
|-------|-----------|----------|---------|
| **Keystroke** | Random Forest | 140 | Classify genuine vs impostor typing |
| **Mouse** | One-Class SVM | 38 | Detect anomalous mouse behavior |
| **App Usage** | Markov Chain | N/A | Model app transition patterns |

All models are trained locally on your machine using your behavioral data collected by SecLyzer.

---

## Prerequisites

### System Requirements

- **OS:** Linux (Ubuntu 20.04+, Debian, Arch)
- **Python:** 3.12+ (with venv activated)
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 500MB for models and training data
- **CPU:** Multi-core recommended (training uses parallel processing)

### Software Requirements

```bash
# Python packages (already installed if you ran install.sh)
scikit-learn>=1.3.0
pandas>=2.0.0
joblib>=1.3.0
onnx>=1.14.0
skl2onnx>=1.15.0
onnxruntime>=1.16.0
influxdb-client>=1.36.0
polars>=0.19.0
numpy>=1.24.0
```

### Data Requirements

Before training, you need sufficient behavioral data:

| Model | Minimum | Recommended | Typical Collection Time |
|-------|---------|-------------|------------------------|
| Keystroke | 500 samples | 1000+ samples | 2-3 days |
| Mouse | 800 samples | 1500+ samples | 3-4 days |
| App Usage | 50 transitions | 100+ transitions | 1-2 days |

**Note:** Data is collected automatically while you use your computer. The extractors must be running.

---

## Quick Start

### 1. Check Data Availability

```bash
# Activate virtual environment
source ~/.seclyzer-venv/bin/activate
cd ~/SecLyzer

# Check if you have enough data
python scripts/train_models.py --check
```

**Expected Output:**
```
📊 Checking Data Availability...

✅ Keystroke:    1234 samples
   Status: OPTIMAL
   Progress: 123.4% of recommended
   Required: 500 | Recommended: 1000

✅ Mouse:        1876 samples
   Status: OPTIMAL
   Progress: 125.1% of recommended
   Required: 800 | Recommended: 1500

✅ App:           156 samples
   Status: READY
   Progress: 156.0% of recommended
   Required: 50 | Recommended: 100
```

### 2. Train All Models

```bash
# Train all three models
python scripts/train_models.py --all
```

### 3. Verify Models

```bash
# Check that models were saved
ls -lh data/models/

# Output should show:
# keystroke_rf_v1.0.0_YYYYMMDD_HHMMSS.pkl
# keystroke_rf_v1.0.0_YYYYMMDD_HHMMSS.onnx
# mouse_svm_v1.0.0_YYYYMMDD_HHMMSS.pkl
# mouse_svm_v1.0.0_YYYYMMDD_HHMMSS.onnx
# app_markov_v1.0.0_YYYYMMDD_HHMMSS.json
```

---

## Model Details

### 1. Keystroke Model (Random Forest)

**Purpose:** Distinguish between you (genuine user) and impostors based on typing patterns.

#### Features (140 total)

1. **Dwell Time (8 features)**
   - Mean, std, min, max, median, Q25, Q75, range
   - How long each key is held down

2. **Flight Time (8 features)**
   - Mean, std, min, max, median, Q25, Q75, range
   - Time between releasing one key and pressing the next

3. **Digraphs (20 features)**
   - Top 20 most common 2-key combinations
   - Example: "th", "he", "in", "er"

4. **Error Patterns (4 features)**
   - Backspace frequency
   - Correction rate
   - Clean typing ratio
   - Error patterns

5. **Rhythm (8 features)**
   - Typing consistency
   - Burst frequency (rapid typing)
   - Pause frequency
   - Average burst speed
   - Average pause duration
   - Variation metrics
   - Typing speed (WPM)
   - Rhythm stability

#### Algorithm Configuration

```python
RandomForestClassifier(
    n_estimators=50,      # 50 trees (laptop-optimized)
    max_depth=15,         # Prevent overfitting
    min_samples_split=10,
    min_samples_leaf=5,
    max_features='sqrt',  # Faster than 'auto'
    n_jobs=-1,            # Use all CPU cores
    class_weight='balanced'
)
```

#### Training Process

1. Fetch positive samples (your typing) from InfluxDB
2. Generate synthetic negative samples (impostor attempts)
   - Add Gaussian noise
   - Permute features randomly
   - Ratio: 30% negative, 70% positive
3. Split into train/test (80/20)
4. Train Random Forest
5. Evaluate on test set
6. Export to PKL and ONNX formats

#### Expected Performance

- **Accuracy:** 85-95% (depending on data quality)
- **Training Time:** 10-30 seconds on laptop
- **Model Size:** ~5-15 MB

---

### 2. Mouse Model (One-Class SVM)

**Purpose:** Detect anomalous mouse behavior that differs from your normal patterns.

#### Features (38 total)

1. **Movement Features (20)**
   - Velocity (mean, std, max, median)
   - Acceleration (mean, std, max)
   - Curvature, angle changes
   - Jerk (smoothness indicator)
   - Distance metrics
   - Idle time
   - Movement frequency

2. **Click Features (10)**
   - Click duration (mean, std)
   - Left/right/middle click counts
   - Click ratios
   - Double-click detection
   - Click frequency

3. **Scroll Features (8)**
   - Scroll delta (mean, std)
   - Up/down scroll counts
   - Scroll direction ratio
   - Scroll frequency
   - Scroll intervals

#### Algorithm Configuration

```python
OneClassSVM(
    kernel='rbf',         # Radial basis function
    gamma='scale',        # Auto-scale gamma
    nu=0.1,              # 10% outlier fraction
    cache_size=500,      # 500MB cache (laptop-friendly)
    max_iter=1000        # Iteration limit
)
```

#### Training Process

1. Fetch normal samples (your mouse behavior) from InfluxDB
2. Scale features using StandardScaler (critical for SVM)
3. Reserve 20% for testing
4. Train One-Class SVM on normal data only
5. Generate synthetic anomalies for evaluation
   - Extreme value injection (50%)
   - Pattern disruption (50%)
6. Evaluate on test set (normal + anomalies)
7. Export to PKL and ONNX formats (with embedded scaler)

#### Expected Performance

- **Accuracy:** 80-90% (on normal + anomaly test set)
- **AUC:** 0.75-0.90
- **Training Time:** 15-45 seconds on laptop
- **Model Size:** ~2-8 MB

---

### 3. App Usage Model (Markov Chain)

**Purpose:** Model your application switching patterns and time-of-day preferences.

#### Components

1. **Markov Chain Transition Matrix**
   - Probability of switching from App A to App B
   - Example: P(firefox → chrome) = 0.23
   - Stored as dictionary: `{"firefox->chrome": 0.23}`

2. **Time-of-Day Patterns**
   - Hourly usage distribution per app
   - Example: Firefox mostly used 9am-5pm
   - Peak hour identification

3. **Duration Statistics**
   - Mean, std, median, min, max duration per app
   - Sample counts

4. **App Rankings**
   - Top 20 most-used applications
   - Usage frequency counts

#### Training Process

1. Fetch app transitions from InfluxDB
2. Build transition probability matrix
3. Calculate time-of-day patterns
4. Compute duration statistics
5. Rank applications by usage
6. Calculate entropy (predictability metric)
7. Export to JSON format

#### Expected Performance

- **Predictability Score:** 0.6-0.9 (higher = more predictable)
- **Entropy:** 2-6 bits (lower = more predictable)
- **Training Time:** <5 seconds
- **Model Size:** ~10-100 KB

---

## Training Process

### Standard Training Workflow

#### Step 1: Prepare Environment

```bash
# Activate virtual environment
source ~/.seclyzer-venv/bin/activate
cd ~/SecLyzer
export PYTHONPATH=~/SecLyzer:$PYTHONPATH
```

#### Step 2: Verify Data Collection

```bash
# Check that extractors are running
ps aux | grep extractor

# Should see:
# python3 processing/extractors/keystroke_extractor.py
# python3 processing/extractors/mouse_extractor.py
# python3 processing/extractors/app_tracker.py
```

#### Step 3: Check Data Readiness

```bash
python scripts/train_models.py --check
```

#### Step 4: Train Models

```bash
# Train all models (recommended)
python scripts/train_models.py --all

# Or train specific models
python scripts/train_models.py --keystroke
python scripts/train_models.py --mouse
python scripts/train_models.py --app

# Or combination
python scripts/train_models.py --keystroke --mouse
```

#### Step 5: Verify Results

```bash
# Check models directory
ls -lh data/models/

# Check database metadata
sqlite3 /var/lib/seclyzer/databases/seclyzer.db \
  "SELECT model_type, version, accuracy, trained_at FROM models ORDER BY trained_at DESC LIMIT 5;"
```

### Training Options

#### Time Window

```bash
# Use last 7 days of data
python scripts/train_models.py --all --days 7

# Use last 14 days
python scripts/train_models.py --all --days 14

# Use last 30 days (default)
python scripts/train_models.py --all --days 30
```

#### Force Training

```bash
# Skip data availability checks (not recommended)
python scripts/train_models.py --all --force

# Useful for:
# - Testing with limited data
# - Quick model prototyping
# - Debugging training pipeline
```

#### Custom Output Directory

```bash
# Save models to custom location
python scripts/train_models.py --all --output ./my_models

# Default: data/models/
```

#### Custom User

```bash
# Train for specific user (if multi-user setup)
python scripts/train_models.py --all --user john
```

---

## Performance Optimization

### Laptop-Friendly Configurations

SecLyzer training is optimized for laptops without GPU:

#### 1. Random Forest (Keystroke Model)

**Optimizations:**
- Reduced trees: 50 instead of 100 (50% faster)
- Limited depth: 15 instead of unlimited
- Sqrt features: Faster than considering all features
- Parallel processing: Uses all CPU cores

**Trade-offs:**
- Slightly lower accuracy (~2-3%)
- Much faster training (~50% time reduction)
- Smaller model size

#### 2. One-Class SVM (Mouse Model)

**Optimizations:**
- Limited cache: 500MB instead of 1GB
- Max iterations: 1000 limit
- Shrinking heuristic: Enabled
- RBF kernel: Efficient for laptop CPUs

**Trade-offs:**
- Slightly lower precision on edge cases
- Much faster convergence
- Lower memory usage

#### 3. Markov Chain (App Model)

**Optimizations:**
- Pure Python implementation (no ML libraries)
- Efficient dictionary structures
- Minimal memory footprint
- JSON output (fast serialization)

**Trade-offs:**
- None (already very efficient)

### Training Time Estimates

| Model | Minimum Samples | Typical Training Time |
|-------|----------------|---------------------|
| Keystroke | 500 | 10-20 seconds |
| Keystroke | 1000 | 15-30 seconds |
| Mouse | 800 | 15-30 seconds |
| Mouse | 1500 | 20-45 seconds |
| App Usage | 50 | 2-5 seconds |
| App Usage | 100 | 3-7 seconds |

**Hardware tested:** Intel i5-8250U (4 cores), 8GB RAM

### Memory Usage

| Model | Peak Memory | Disk Space |
|-------|------------|------------|
| Keystroke | 200-500 MB | 5-15 MB |
| Mouse | 150-400 MB | 2-8 MB |
| App Usage | 50-100 MB | 10-100 KB |

---

## Troubleshooting

### Error: Insufficient Data

```
❌ Insufficient data for the following models:
   - keystroke: 234 samples (need 500)
```

**Solutions:**
1. **Wait longer:** Let extractors run for more days
2. **Check extractors:** Verify they're running (`ps aux | grep extractor`)
3. **Lower requirements:** Use `--force` flag (not recommended)
4. **Reduce time window:** Use `--days 7` instead of `--days 30`

### Error: Database Connection Failed

```
❌ Training failed: Failed to connect to InfluxDB
```

**Solutions:**
1. Check InfluxDB is running: `systemctl status influxdb`
2. Test connection: `curl http://localhost:8086/ping`
3. Check token: `cat /etc/seclyzer/influxdb_token`
4. Restart InfluxDB: `sudo systemctl restart influxdb`

### Error: Out of Memory

```
MemoryError: Unable to allocate array
```

**Solutions:**
1. Close other applications
2. Reduce time window: `--days 7`
3. Train models separately instead of `--all`
4. Increase swap space

### Warning: Low Accuracy

```
Model Performance:
   Accuracy:  0.6234  (WARNING: Low accuracy)
```

**Solutions:**
1. **Collect more data:** Current data may be insufficient
2. **Check data quality:** Look for dev_mode data mixed in
3. **Increase time window:** Use `--days 30` instead of `--days 7`
4. **Re-train later:** Accuracy improves with more data

### Error: ONNX Conversion Failed

```
❌ Failed to convert model to ONNX format
```

**Solutions:**
1. Check `skl2onnx` version: `pip show skl2onnx`
2. Update ONNX: `pip install --upgrade onnx skl2onnx`
3. PKL model is still saved and usable
4. ONNX is only needed for cross-platform inference

---

## Advanced Usage

### Training Individual Models

#### Keystroke Only

```bash
python processing/models/train_keystroke.py \
  --user default \
  --days 30 \
  --min-samples 500 \
  --output data/models
```

#### Mouse Only

```bash
python processing/models/train_mouse.py \
  --user default \
  --days 30 \
  --min-samples 800 \
  --output data/models
```

#### App Usage Only

```bash
python processing/models/train_app_usage.py \
  --user default \
  --days 30 \
  --min-transitions 50 \
  --output data/models
```

### Including Developer Mode Data

By default, data collected in developer mode is excluded from training.

```bash
# Include dev mode data (use with caution)
python processing/models/train_keystroke.py --include-dev-mode
python processing/models/train_mouse.py --include-dev-mode
python processing/models/train_app_usage.py --include-dev-mode
```

**When to use:**
- Testing training pipeline
- Generating demo models
- Development debugging

**When NOT to use:**
- Production models
- Final deployment
- When authentication is enabled

### Re-training Models

Models are versioned with timestamps. Old models are not deleted automatically.

```bash
# Train new version
python scripts/train_models.py --all

# Compare versions
ls -lt data/models/

# Keep multiple versions for A/B testing
```

### Loading Trained Models

```python
import joblib

# Load keystroke model
model_data = joblib.load('data/models/keystroke_rf_v1.0.0_20251202_143022.pkl')
model = model_data['model']
feature_names = model_data['feature_names']
metrics = model_data['metrics']

print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"Features: {feature_names[:10]}")

# Load mouse model
model_data = joblib.load('data/models/mouse_svm_v1.0.0_20251202_143045.pkl')
model = model_data['model']
scaler = model_data['scaler']

# Load app model
import json
with open('data/models/app_markov_v1.0.0_20251202_143050.json', 'r') as f:
    app_model = json.load(f)

transitions = app_model['markov_chain']['transitions']
```

### Using ONNX Models

```python
import onnxruntime as rt

# Load ONNX model
sess = rt.InferenceSession('data/models/keystroke_rf_v1.0.0_20251202_143022.onnx')

# Prepare input
import numpy as np
X = np.random.randn(1, 140).astype(np.float32)

# Run inference
input_name = sess.get_inputs()[0].name
output_name = sess.get_outputs()[0].name
prediction = sess.run([output_name], {input_name: X})

print(f"Prediction: {prediction}")
```

---

## Best Practices

### 1. Data Collection

- ✅ Let extractors run for at least 1 week before training
- ✅ Use computer naturally (don't change behavior)
- ✅ Exclude developer mode data from training
- ✅ Collect during normal work hours for best app patterns

### 2. Training Schedule

- ✅ Train once you have 1000+ keystroke and 1500+ mouse samples
- ✅ Re-train every 1-2 months to adapt to changes
- ✅ Keep multiple model versions for comparison
- ✅ Test models before deploying to production

### 3. Model Management

- ✅ Use timestamped versions (automatic)
- ✅ Keep PKL and ONNX versions
- ✅ Back up trained models regularly
- ✅ Document model performance in CHANGELOG.md

### 4. Performance

- ✅ Train all models at once with `--all`
- ✅ Use default laptop-optimized settings
- ✅ Close other applications during training
- ✅ Monitor memory usage with `htop`

---

## Related Documentation

- **Architecture:** See `ARCHITECTURE.md` for system design
- **Control Scripts:** See `docs/CONTROL_SCRIPTS.md` for dev/seclyzer commands
- **Changelog:** See `CHANGELOG.md` for training implementation details
- **Testing:** See `tests/models/` for training tests

---

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review test output: `pytest tests/models/ -v`
3. Check logs: `/var/log/seclyzer/*.log`
4. Open GitHub issue with model output and error logs

---

**Last Updated:** December 2, 2025  
**Version:** 1.0.0  
**Status:** Production Ready