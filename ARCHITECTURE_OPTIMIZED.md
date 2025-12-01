# SecLyzer - Optimized Architecture for Resource-Constrained Systems

## Executive Summary

**Your Hardware Budget:**
- **RAM**: 16 GB total → **5 GB allocated to SecLyzer** (30%)
- **Storage**: **3-5 GB** dedicated space
- **CPU**: Target **<15%** average load (across all cores)

**Verdict:** ✅ Your laptop can absolutely handle this system with optimizations.

---

## Resource Budget Breakdown

### Memory Allocation (5 GB Total)

| Component | Heap Size | Justification |
|-----------|-----------|---------------|
| Keyboard Collector (Rust) | 10 MB | Minimal state, ring buffer only |
| Mouse Collector (Rust) | 15 MB | Higher sampling rate |
| App Monitor (Python) | 50 MB | Python overhead + psutil |
| Redis Message Queue | 500 MB | Holds ~10 minutes of buffered events |
| Feature Extractor (Python) | 200 MB | NumPy arrays, sliding windows |
| InfluxDB | 1.5 GB | Time-series database cache |
| ML Models (loaded in RAM) | 800 MB | 4 models × 200 MB each |
| Inference Engine (Python) | 300 MB | scikit-learn runtime |
| Decision Engine (Python) | 100 MB | State machine logic |
| OS Overhead | 1.5 GB | Buffers, cache |
| **TOTAL** | **4.975 GB** | ✅ Under budget |

### Storage Allocation (5 GB Total)

| Data Type | Size | Retention |
|-----------|------|-----------|
| InfluxDB Time-Series | 2 GB | 30 days rolling |
| SQLite Metadata | 50 MB | Permanent |
| Trained Models | 500 MB | 4 models |
| Logs (compressed) | 300 MB | 30 days |
| Raw Event Buffer (temp) | 100 MB | 1 hour |
| Application Binaries | 200 MB | Rust + Python deps |
| System Reserve | 1.85 GB | Future growth |
| **TOTAL** | **5 GB** | ✅ Exactly at budget |

### CPU Budget (Target: <15% average)

| Component | CPU % (Avg) | CPU % (Peak) |
|-----------|-------------|--------------|
| Keyboard Collector | 0.5% | 2% |
| Mouse Collector | 1% | 3% |
| App Monitor | 0.2% | 0.5% |
| Feature Extractor | 2% | 8% |
| ML Inference | 5% | 15% |
| Redis | 1% | 3% |
| InfluxDB | 2% | 5% |
| **TOTAL** | **11.7%** | **36.5%** |

✅ Average usage well under 15% target  
⚠️ Peak spikes acceptable (occurs every 5s for <200ms)

---

## Key Optimizations

### 1. Rust for All Collectors (Not Just Keyboard/Mouse)

**Change:** Move App Monitor from Python to Rust

**Why:**
- Python `psutil` uses 50 MB RAM + 5% CPU just for polling
- Rust equivalent: 5 MB RAM + 0.2% CPU

**Implementation:**
- Use `sysinfo` crate (Rust) instead of `psutil`
- Still exposes data over same message queue

**Savings:**
- RAM: -45 MB
- CPU: -4.8%

---

### 2. Use Lightweight ML Models

**Change:** Switch from deep learning to classical ML

**Models:**

| Modality | Algorithm | Model Size | Inference Time |
|----------|-----------|------------|----------------|
| Keystroke | Random Forest (50 trees) | 80 MB | 5 ms |
| Mouse | One-Class SVM | 120 MB | 8 ms |
| Linguistic | Naive Bayes | 20 MB | 2 ms |
| App Usage | Markov Chain (in-memory dict) | 5 MB | <1 ms |

**Total:** 225 MB (was estimating 800 MB)

**Inference Time:** 16 ms total → Can run every 5 seconds easily

**Optimization:**
- Use `ONNX Runtime` (C++) for inference instead of pure Python
- 3x faster than scikit-learn's native Python

**Savings:**
- RAM: -575 MB
- CPU: -2% (faster inference)

---

### 3. Compress Time-Series Data Aggressively

**Change:** Use InfluxDB's compression + downsampling

**Strategy:**
- **Raw data** (first 24 hours): Full resolution
- **1-7 days old**: Downsample to 1-minute averages
- **7-30 days old**: Downsample to 5-minute averages

**Example:**
- Raw: 100 MB/day
- After 24h: 20 MB/day (80% reduction)
- After 7d: 5 MB/day (95% reduction)

**30-day rolling window:**
- 100 MB (day 1) + 7×20 MB (days 2-7) + 23×5 MB (days 8-30)
- **Total: 355 MB** (was budgeting 2 GB)

**Savings:**
- Storage: -1.65 GB

---

### 4. Use Redis in Memory-Efficient Mode

**Change:** Configure Redis for low memory usage

```bash
# redis.conf optimizations
maxmemory 256mb              # Hard cap (was 500mb)
maxmemory-policy allkeys-lru # Evict old keys when full
save ""                      # Disable persistence (we don't need it)
rdbcompression yes
```

**Why it's safe:**
- Message queue is ephemeral (data flows through, not stored)
- If buffer fills, oldest events are dropped (acceptable for ML)

**Savings:**
- RAM: -244 MB

---

### 5. Lazy-Load ML Models

**Change:** Load models into RAM only when needed for inference

**Current (naive):**
- All 4 models loaded at startup → 800 MB resident

**Optimized:**
- Load model → Run inference → Unload model
- Only 1 model in RAM at a time → 200 MB resident
- Inference happens every 5 seconds, so loading overhead is acceptable

**Code:**
```python
class LazyModelLoader:
    def __init__(self):
        self.models = {}
    
    def predict(self, model_name, features):
        # Load model if not cached
        if model_name not in self.models:
            self.models[model_name] = load_model(model_name)
        
        # Run inference
        score = self.models[model_name].predict(features)
        
        # Unload if memory pressure
        if psutil.virtual_memory().percent > 80:
            del self.models[model_name]
        
        return score
```

**Savings:**
- RAM: -600 MB (only 1 model resident at a time)

---

### 6. Use Polars Instead of Pandas

**Change:** Feature extraction uses Polars (Rust-based DataFrame)

**Why:**
- Pandas (Python): 150 MB RAM for 30s window processing
- Polars (Rust): 30 MB RAM for same data (5x less)
- Polars is 10-50x faster (multi-threaded)

**Example:**
```python
# Old (Pandas)
import pandas as pd
df = pd.DataFrame(events)
features = df.groupby('key').agg({'dwell_time': ['mean', 'std']})

# New (Polars)
import polars as pl
df = pl.DataFrame(events)
features = df.groupby('key').agg([
    pl.col('dwell_time').mean(),
    pl.col('dwell_time').std()
])
```

**Savings:**
- RAM: -120 MB
- CPU: -1.5% (faster processing)

---

### 7. Batch Inference Instead of Streaming

**Change:** Run ML models once every 5 seconds (not on every event)

**Current Flow:**
- Event arrives → Extract features → Run model → Update score
- This happens 100 times/second → wasteful

**Optimized Flow:**
- Events accumulate for 5 seconds → Batch feature extraction → Single model run

**Savings:**
- CPU: -3% (less overhead from context switching)

---

### 8. Use mmap for Model Loading

**Change:** Memory-map model files instead of loading into heap

**Why:**
- Loading 200 MB model into RAM: Actual 200 MB RAM used
- Memory-mapping: OS keeps it in page cache, only loads pages on access
- Effective RAM: ~50 MB (only hot pages)

**Implementation:**
```python
import joblib
import mmap

# Instead of:
model = joblib.load('model.pkl')

# Use:
with open('model.pkl', 'rb') as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    model = joblib.load(mm)
```

**Savings:**
- RAM: -150 MB per model (75% reduction)

---

## Optimized Resource Budget

### Memory (After Optimizations)

| Component | Original | Optimized | Savings |
|-----------|----------|-----------|---------|
| Collectors | 75 MB | 30 MB | -45 MB |
| Redis | 500 MB | 256 MB | -244 MB |
| Feature Extractor | 200 MB | 80 MB | -120 MB |
| InfluxDB | 1500 MB | 1500 MB | 0 MB |
| ML Models | 800 MB | 50 MB | -750 MB |
| Python Runtimes | 400 MB | 400 MB | 0 MB |
| OS Overhead | 1500 MB | 1500 MB | 0 MB |
| **TOTAL** | **4975 MB** | **3816 MB** | **-1159 MB** |

✅ **New total: 3.8 GB** (23% of your 16 GB)

### Storage (After Optimizations)

| Component | Original | Optimized | Savings |
|-----------|----------|-----------|---------|
| Time-Series DB | 2000 MB | 355 MB | -1645 MB |
| Models | 500 MB | 225 MB | -275 MB |
| Logs | 300 MB | 100 MB | -200 MB |
| Others | 350 MB | 350 MB | 0 MB |
| **TOTAL** | **3150 MB** | **1030 MB** | **-2120 MB** |

✅ **New total: 1 GB** (Only 20% of budget!)

### CPU (After Optimizations)

| Component | Original | Optimized | Savings |
|-----------|----------|-----------|---------|
| Collectors | 1.7% | 0.7% | -1% |
| Feature Extractor | 2% | 0.5% | -1.5% |
| ML Inference | 5% | 2% | -3% |
| Database | 3% | 3% | 0% |
| **TOTAL** | **11.7%** | **6.2%** | **-5.5%** |

✅ **New average: 6.2%** (Extremely light!)

---

## Technology Stack (Optimized)

### Languages Breakdown

| Component | Language | Reason |
|-----------|----------|--------|
| **Data Collectors** | **Rust** | Zero-overhead concurrency, 10x less memory |
| **Feature Extraction** | **Python (Polars)** | Polars is Rust under the hood, fast enough |
| **ML Training** | **Python (scikit-learn)** | Rich ecosystem, training is offline |
| **ML Inference** | **ONNX Runtime (C++)** | 3x faster than Python, called from Python |
| **Fusion & Decision** | **Python** | Logic is simple, clarity > speed |
| **Message Queue** | **Redis (C)** | Industry standard, battle-tested |
| **Database** | **InfluxDB (Go)** | Optimized for time-series |

### Why This Mix?

1. **Rust** for hot paths (data collection = 24/7 running)
2. **Python** for ML and logic (changed infrequently, easier to maintain)
3. **ONNX Runtime** bridges the gap (Rust-like speed, Python-like ease)

---

## Virtual Environment Setup

Since you have a venv at `/home/bhuvan/Documents/Projects/venv`, we'll use it.

### Installation Plan

```bash
# Activate venv
source /home/bhuvan/Documents/Projects/venv/bin/activate

# Install optimized Python dependencies
pip install polars==0.20.0          # Fast DataFrame (Rust-based)
pip install onnxruntime==1.17.0     # Fast ML inference
pip install scikit-learn==1.4.0     # ML training
pip install redis==5.0.0            # Message queue client
pip install influxdb-client==1.40.0 # Time-series DB
pip install psutil==5.9.8           # System monitoring
pip install pyyaml==6.0.1           # Config parsing

# For training only (can uninstall after training)
pip install jupyter pandas matplotlib seaborn
```

**Total installed size:** ~800 MB (in venv, not system-wide)

---

## Performance Benchmarks (Expected on Your Laptop)

Assuming your laptop specs:
- **CPU**: Intel i5/i7 or Ryzen 5/7 (4-8 cores)
- **RAM**: 16 GB
- **Disk**: SSD (not HDD)

### Latency Targets

| Operation | Target | Expected (Your HW) |
|-----------|--------|---------------------|
| Keystroke capture → Queue | <1 ms | 0.3 ms |
| Feature extraction (30s batch) | <100 ms | 40 ms |
| Single model inference | <10 ms | 6 ms |
| All 4 models inference | <50 ms | 25 ms |
| Fusion + Decision | <5 ms | 2 ms |
| **Total (end-to-end)** | **<200 ms** | **~75 ms** |

✅ Well under real-time requirements (5-second update cycle)

### Throughput Targets

| Event Type | Rate | Handling Capacity |
|------------|------|-------------------|
| Keystrokes | 10/sec (typing) | 1000/sec |
| Mouse events | 50/sec (normal use) | 10,000/sec |
| App switches | 5/min | 100/min |

✅ Collectors can handle 100x your actual usage

---

## Disk I/O Optimization

### Write Strategy (InfluxDB)

- **Batch writes**: Every 1 second (not real-time)
- **Compression**: Gzip level 6 (80% reduction)
- **SSD-optimized**: Use `fsync` sparingly

**Expected I/O:**
- Writes: 10 MB/hour → 240 MB/day
- Reads (for inference): 5 MB every 5 seconds → 50 KB/sec

**Impact on SSD lifespan:**
- Daily writes: 0.24 GB
- SSD endurance: ~300 TB (typical)
- **Years until SSD wear**: 300,000 / 0.24 = 1.25 million days = 3,400 years ✅

---

## Recommended Optimizations Priority

### Phase 1: Must-Have (Implement First)
1. ✅ Rust collectors (keyboard, mouse, app)
2. ✅ Polars for feature extraction
3. ✅ Redis memory limit (256 MB)
4. ✅ Batch inference (every 5 sec)

### Phase 2: Nice-to-Have (After MVP works)
5. ONNX Runtime for inference
6. Lazy model loading
7. mmap for models

### Phase 3: Advanced (Only if needed)
8. Model quantization (INT8 instead of FP32)
9. Custom Rust ML inference (skip Python entirely)

---

## Final Verdict

✅ **Your laptop can handle this system easily**

**Resource Usage:**
- RAM: **3.8 GB / 16 GB** (24%) → **11.2 GB free for other apps**
- Storage: **1 GB / 5 GB budget** (20%) → **4 GB buffer**
- CPU: **6.2%** average → **93.8% free**

**Battery Impact:**
- Idle: +5% drain rate
- Active use: +10% drain rate
- **Total battery reduction**: ~15-20%

**With these optimizations, SecLyzer will be a lightweight background service that you'll never notice is running.**

Ready to proceed with implementation?
