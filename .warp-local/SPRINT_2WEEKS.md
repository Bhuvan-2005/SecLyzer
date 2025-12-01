# SecLyzer: 2-Week Sprint to MVP
**Goal:** Move from 4.5/10 to 6.5/10 production readiness  
**Effort:** 80 hours (10 hours/day, 8 days focus)  
**Outcome:** Fully functional authentication system (data→decision), code quality enforcement, basic monitoring

---

## WEEK 1: Core Functionality (40 hours)

### Day 1-2: ML Training Pipeline (16 hours)
**Goal:** Build `training/train_keystroke.py` and verify it works with your data

#### 1.1 Create Training Directory Structure
```bash
mkdir -p training/{models,reports,data}
touch training/__init__.py
touch training/train_keystroke.py
touch training/train_mouse.py
touch training/evaluate.py
```

#### 1.2 Build `training/train_keystroke.py` (~400 lines)
```python
#!/usr/bin/env python3
"""
Train keystroke authentication model.
Input: Keystroke features from InfluxDB (past 2 weeks)
Output: ONNX model saved to training/models/keystroke_model.onnx
"""

import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
import skl2onnx
from skl2onnx.common.data_types import FloatTensorType

from storage.timeseries import TimeSeries
from storage.database import Database
from common.config import Config
from common.logger import get_logger

logger = get_logger(__name__)
config = Config()

class KeystrokeTrainer:
    def __init__(self, days_back=14):
        self.days_back = days_back
        self.db = Database()
        self.ts = TimeSeries()
        self.model = None
        self.scaler = StandardScaler()
        
    def fetch_positive_samples(self):
        """Fetch keystroke features from InfluxDB (legitimate user)"""
        start_time = datetime.now() - timedelta(days=self.days_back)
        query = f"""
        from(bucket:"{self.ts.bucket}")
        |> range(start: {start_time.isoformat()}Z)
        |> filter(fn: (r) => r["_measurement"] == "keystroke_features")
        |> filter(fn: (r) => r["dev_mode"] == "false")
        """
        
        try:
            records = self.ts.query_keystroke_features(query)
            logger.info(f"Fetched {len(records)} positive keystroke samples")
            return records
        except Exception as e:
            logger.error(f"Failed to fetch positive samples: {e}")
            raise
    
    def fetch_negative_samples(self):
        """Download public keystroke datasets (CMU, Clarkson)"""
        # For now, generate synthetic negatives from positive data
        # In production: download from CMU-Palestra or Clarkson datasets
        logger.warning("Using synthetic negatives (TODO: download real datasets)")
        return self._generate_synthetic_negatives()
    
    def _generate_synthetic_negatives(self):
        """Generate synthetic negatives by permuting features"""
        positive = self.fetch_positive_samples()
        negatives = []
        for sample in positive:
            # Permute: slow down all timings by 50% (different typing style)
            permuted = {k: v * 1.5 if k in ['dwell_mean', 'flight_mean'] else v 
                       for k, v in sample.items()}
            negatives.append(permuted)
        return negatives
    
    def prepare_data(self):
        """Load and label training data"""
        positive = self.fetch_positive_samples()
        negative = self.fetch_negative_samples()
        
        if len(positive) < 100:
            raise ValueError(f"Need at least 100 positive samples, got {len(positive)}")
        
        X = []
        y = []
        
        # Positive samples (label=1)
        for sample in positive:
            features = [sample.get(f, 0) for f in self.get_feature_names()]
            X.append(features)
            y.append(1)
        
        # Negative samples (label=0)
        for sample in negative:
            features = [sample.get(f, 0) for f in self.get_feature_names()]
            X.append(features)
            y.append(0)
        
        X = np.array(X, dtype=np.float32)
        y = np.array(y)
        
        logger.info(f"Prepared data: {len(X)} samples, {X.shape[1]} features")
        logger.info(f"Class distribution: {np.bincount(y)} (pos:neg)")
        
        return X, y
    
    def train(self):
        """Train Random Forest classifier"""
        X, y = self.prepare_data()
        
        # Split: 80% train, 20% test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train = self.scaler.fit_transform(X_train)
        X_test = self.scaler.transform(X_test)
        
        # Hyperparameter tuning
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [10, 20],
            'min_samples_split': [2, 5],
        }
        
        rf = RandomForestClassifier(random_state=42, n_jobs=-1)
        grid_search = GridSearchCV(rf, param_grid, cv=5, n_jobs=-1, verbose=1)
        grid_search.fit(X_train, y_train)
        
        self.model = grid_search.best_estimator_
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        logger.info(f"Train accuracy: {train_score:.3f}, Test accuracy: {test_score:.3f}")
        
        # Save model
        self.save_model(X_train)
        self.save_scaler()
        
        # Save metadata to database
        self.db.save_model_metadata(
            model_type="keystroke",
            version="1.0.0",
            accuracy=test_score,
            model_path="training/models/keystroke_model.onnx"
        )
    
    def save_model(self, X_train):
        """Convert to ONNX and save"""
        initial_type = [('float_input', FloatTensorType([None, X_train.shape[1]]))]
        
        onnx_model = skl2onnx.convert_sklearn(
            self.model, initial_types=initial_type, target_opset=12
        )
        
        model_path = Path("training/models/keystroke_model.onnx")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(model_path, 'wb') as f:
            f.write(onnx_model.SerializeToString())
        
        logger.info(f"Model saved to {model_path}")
    
    def save_scaler(self):
        """Save scaler for inference"""
        scaler_path = Path("training/models/keystroke_scaler.pkl")
        joblib.dump(self.scaler, scaler_path)
        logger.info(f"Scaler saved to {scaler_path}")
    
    @staticmethod
    def get_feature_names():
        """Return list of 140 keystroke features"""
        # This should match keystroke_extractor.py
        return [f"dwell_{stat}" for stat in ['mean', 'std', 'min', 'max', 'median', 'q25', 'q75', 'range']] + \
               [f"flight_{stat}" for stat in ['mean', 'std', 'min', 'max', 'median', 'q25', 'q75', 'range']] + \
               [f"digraph_{i}" for i in range(20)] + \
               [f"error_{type}" for type in ['backspace', 'correction', 'delete', 'undo']] + \
               [f"rhythm_{metric}" for metric in ['consistency', 'burst_freq', 'typing_speed', 'pause_ratio', 
                                                   'acceleration', 'deceleration', 'jitter', 'variance']] + \
               ['dev_mode', 'total_keystrokes']

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14, help="Days of data to use")
    args = parser.parse_args()
    
    trainer = KeystrokeTrainer(days_back=args.days)
    trainer.train()
```

**Acceptance Criteria:**
- [ ] Script runs without errors
- [ ] Saves ONNX model to `training/models/keystroke_model.onnx`
- [ ] Logs accuracy metrics
- [ ] Handles < 100 samples gracefully

#### 1.3 Create Similar Scripts for Mouse & App
- `training/train_mouse.py` - One-Class SVM (~250 lines)
- `training/train_app.py` - Statistical model (~200 lines)

**Time breakdown:**
- Keystroke trainer: 8 hours
- Mouse trainer: 4 hours
- App trainer: 4 hours

---

### Day 3-4: Inference Engine (16 hours)
**Goal:** Build `inference/engine.py` - the actual authentication decision maker

#### 2.1 Create Inference Directory
```bash
mkdir -p inference/{models,logs}
touch inference/__init__.py
touch inference/engine.py
touch inference/trust_scorer.py
touch inference/models.py
```

#### 2.2 Build `inference/engine.py` (~300 lines)
```python
#!/usr/bin/env python3
"""
Real-time inference engine. Scores incoming feature vectors.
Input: 30-second feature vector (140 keystroke + 38 mouse + app features)
Output: Trust score (0-1) + decision (ALLOW/DENY)
"""

import onnxruntime as ort
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Tuple

from common.logger import get_logger
from storage.database import Database

logger = get_logger(__name__)

class InferenceEngine:
    def __init__(self):
        self.keystroke_session = None
        self.mouse_session = None
        self.keystroke_scaler = None
        self.mouse_scaler = None
        self.db = Database()
        self.load_models()
    
    def load_models(self):
        """Load ONNX models and scalers"""
        keystroke_path = Path("training/models/keystroke_model.onnx")
        mouse_path = Path("training/models/mouse_model.onnx")
        
        if not keystroke_path.exists():
            raise FileNotFoundError(f"Model not found: {keystroke_path}")
        
        try:
            self.keystroke_session = ort.InferenceSession(str(keystroke_path))
            if mouse_path.exists():
                self.mouse_session = ort.InferenceSession(str(mouse_path))
            
            # Load scalers
            self.keystroke_scaler = joblib.load("training/models/keystroke_scaler.pkl")
            if mouse_path.exists():
                self.mouse_scaler = joblib.load("training/models/mouse_scaler.pkl")
            
            logger.info("Models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    def score_keystroke(self, features: np.ndarray) -> float:
        """
        Score keystroke features.
        Returns: P(legitimate user) ∈ [0, 1]
        """
        if self.keystroke_session is None:
            return 0.5  # Default: neutral
        
        # Scale
        features_scaled = self.keystroke_scaler.transform(features.reshape(1, -1))
        
        # Inference
        input_name = self.keystroke_session.get_inputs()[0].name
        output_name = self.keystroke_session.get_outputs()[0].name
        
        result = self.keystroke_session.run(
            [output_name],
            {input_name: features_scaled.astype(np.float32)}
        )
        
        # Extract probability
        predictions = result[0][0]
        score = predictions[1]  # P(legitimate)
        
        return float(score)
    
    def score_mouse(self, features: np.ndarray) -> float:
        """Score mouse features. Returns: P(legitimate)"""
        if self.mouse_session is None:
            return 0.5
        
        features_scaled = self.mouse_scaler.transform(features.reshape(1, -1))
        input_name = self.mouse_session.get_inputs()[0].name
        output_name = self.mouse_session.get_outputs()[0].name
        
        result = self.mouse_session.run(
            [output_name],
            {input_name: features_scaled.astype(np.float32)}
        )
        
        return float(result[0][0][1])
    
    def score_app(self, app_sequence: Dict) -> float:
        """
        Score app usage patterns.
        Input: {"sequence": ["vscode", "terminal", "firefox"], "timestamps": [...]}
        Returns: P(legitimate)
        """
        # Load app patterns from database
        patterns = self.db.get_app_patterns()
        
        if not patterns:
            return 0.5
        
        # Calculate probability of sequence
        sequence_prob = 1.0
        apps = app_sequence.get("sequence", [])
        
        for i in range(len(apps) - 1):
            from_app, to_app = apps[i], apps[i+1]
            transition_prob = patterns.get((from_app, to_app), 0.01)  # Smoothing
            sequence_prob *= transition_prob
        
        # Convert to 0-1 range
        score = 1.0 / (1.0 + np.exp(-np.log(sequence_prob)))
        return score
    
    def inference(self, keystroke_features: np.ndarray,
                 mouse_features: np.ndarray,
                 app_sequence: Dict) -> Tuple[float, str]:
        """
        Make authentication decision.
        
        Returns:
            (trust_score, decision)
            trust_score ∈ [0, 1]
            decision ∈ ["ALLOW", "CHALLENGE", "DENY"]
        """
        # Score each modality
        keystroke_score = self.score_keystroke(keystroke_features)
        mouse_score = self.score_mouse(mouse_features)
        app_score = self.score_app(app_sequence)
        
        # Weighted fusion
        trust_score = (
            0.4 * keystroke_score +
            0.3 * mouse_score +
            0.3 * app_score
        )
        
        # Decision threshold
        if trust_score >= 0.8:
            decision = "ALLOW"
        elif trust_score >= 0.5:
            decision = "CHALLENGE"
        else:
            decision = "DENY"
        
        # Log decision
        logger.info(f"Auth decision: {decision} (score={trust_score:.3f})")
        
        # Audit log
        self.db.log_authentication_decision(
            trust_score=trust_score,
            keystroke_score=keystroke_score,
            mouse_score=mouse_score,
            app_score=app_score,
            decision=decision
        )
        
        return trust_score, decision

# Singleton
_engine = None

def get_inference_engine():
    global _engine
    if _engine is None:
        _engine = InferenceEngine()
    return _engine
```

**Acceptance Criteria:**
- [ ] Loads ONNX models without errors
- [ ] Scores feature vectors
- [ ] Returns (trust_score, decision)
- [ ] Logs all decisions to database

#### 2.3 Create `inference/trust_scorer.py`
Weighted combination logic (50 lines)

**Time breakdown:**
- Engine architecture: 6 hours
- Model loading & scoring: 6 hours
- Testing & debugging: 4 hours

---

### Day 5: Wire Everything Together (8 hours)
**Goal:** Make extractors feed inference engine

#### 3.1 Modify `processing/extractors/keystroke_extractor.py`
Add at end of `_save_features()`:
```python
from inference.engine import get_inference_engine

# After saving to DB/Redis:
engine = get_inference_engine()
trust_score, decision = engine.inference(
    keystroke_features=features_vector,
    mouse_features=mouse_vector,
    app_sequence=app_data
)

# Publish decision to Redis
redis_client.publish("seclyzer:decisions", json.dumps({
    "timestamp": datetime.now().isoformat(),
    "decision": decision,
    "trust_score": trust_score
}))
```

#### 3.2 Add Command to `scripts/dev`
```bash
./scripts/dev train-all  # Trains all three models
./scripts/dev inference-test  # Tests inference on sample data
```

**Time:** 8 hours (6 hours integration, 2 hours testing)

---

## WEEK 2: Code Quality & Monitoring (40 hours)

### Day 6-7: Linting & Type Safety (16 hours)

#### 4.1 Add Python Packaging (2 hours)
Create `pyproject.toml`:
```toml
[project]
name = "seclyzer"
version = "0.2.0"
description = "Behavioral biometric authentication"
requires-python = ">=3.9"

dependencies = [
    "influxdb-client>=1.36.0,<2.0",
    "polars>=0.19.0,<1.0",
    "scikit-learn>=1.3.0,<2.0",
    "onnxruntime>=1.16.0,<2.0",
    "redis>=5.0.0,<6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black>=23.0",
    "flake8>=6.0",
    "mypy>=1.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```

#### 4.2 Install Linting Tools (2 hours)
```bash
source /home/bhuvan/Documents/Projects/venv/bin/activate
pip install black flake8 mypy ruff
```

#### 4.3 Auto-Format All Code (4 hours)
```bash
black . --line-length=100
isort . --profile black
```

#### 4.4 Fix Type Errors (8 hours)
```bash
mypy . --strict 2>&1 | head -100  # See worst offenders
# Gradually add type hints to modules
```

**Priorities (fix most critical first):**
1. `processing/extractors/keystroke_extractor.py` - Missing type hints everywhere
2. `storage/*.py` - Database access functions need types
3. `common/config.py` - Config getter/setter types

#### 4.5 Add Pre-commit Hooks (2 hours)
Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
```

**Time breakdown:**
- pyproject.toml: 2 hours
- Tool installation & config: 2 hours
- Auto-formatting: 4 hours
- Type hints: 8 hours
- Pre-commit: 2 hours
- **Total: 16 hours** ✓

---

### Day 8: Monitoring & Documentation (16 hours)

#### 5.1 Add Prometheus Metrics (6 hours)
Create `common/metrics.py`:
```python
from prometheus_client import Counter, Histogram, Gauge

# Event counts
keystroke_events = Counter('keystroke_events_total', 'Total keystroke events')
mouse_events = Counter('mouse_events_total', 'Total mouse events')

# Feature extraction latency
extraction_latency = Histogram(
    'extraction_latency_seconds',
    'Feature extraction latency',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

# Authentication decisions
auth_decisions = Counter(
    'auth_decisions_total',
    'Authentication decisions',
    ['decision']  # ALLOW, CHALLENGE, DENY
)

# System health
redis_latency = Histogram('redis_latency_ms', 'Redis operation latency')
influx_latency = Histogram('influx_latency_ms', 'InfluxDB operation latency')
```

Emit metrics from extractors:
```python
from common.metrics import keystroke_events, extraction_latency

keystroke_events.inc()

with extraction_latency.time():
    features = extract_keystroke_features(events)
```

Add metrics endpoint to `scripts/dev`:
```bash
./scripts/dev metrics  # Exports Prometheus metrics
# Output: http://localhost:9090/metrics
```

#### 5.2 Create Grafana Dashboard (4 hours)
Save JSON to `monitoring/grafana_dashboard.json`:
- Event rates (events/sec)
- Extraction latency (p50, p95, p99)
- Authentication decision distribution
- Model accuracy trends
- Error rates

#### 5.3 Write Threat Model (3 hours)
Create `docs/THREAT_MODEL.md`:
```markdown
# Security Threat Model

## Assets Protected
- User authentication state
- Behavioral biometric data
- ML models

## Threats & Mitigations
1. **Physical access**: Attacker gets keyboard/mouse
   - Mitigation: 30-second authentication window is short
   
2. **Network access**: Attacker intercepts Redis
   - Mitigation: Local-only, no network exposure
   
3. **Data theft**: Attacker exfiltrates collected data
   - Mitigation: Encrypt at rest, no cloud backup
   
4. **Model poisoning**: Attacker injects false data during training
   - Mitigation: Dev mode data explicitly marked, can be excluded

## Assumptions
- Host OS is trusted (no kernel-level rootkits)
- Hardware is secure (no keyloggers)
- Only local users, no remote access
```

#### 5.4 Update README with New Sections (2 hours)
Add:
- "How to Train Models" section
- "Monitoring" section with Grafana link
- "Performance Tuning" section
- "Security Considerations" section

#### 5.5 Write TROUBLESHOOTING.md (1 hour)
Common issues:
- "No models found" → Run `./scripts/dev train-all`
- "Authentication always denies" → Check model accuracy, retrain
- "High latency in inference" → Check Redis/InfluxDB health

**Time breakdown:**
- Metrics implementation: 6 hours
- Grafana dashboard: 4 hours
- Threat model: 3 hours
- Documentation: 3 hours
- **Total: 16 hours** ✓

---

## FINAL OUTPUT (by end of week 2)

### Functional Improvements
- ✅ **Inference engine works** (data→decision)
- ✅ **Models trained & validated**
- ✅ **End-to-end pipeline operational**
- ✅ **Monitoring visible** (Prometheus + Grafana)

### Code Quality
- ✅ **Linting passes** (black, flake8, ruff)
- ✅ **Type checking passes** (mypy --strict)
- ✅ **Pre-commit hooks installed**
- ✅ **pyproject.toml published to PyPI-ready**

### Documentation
- ✅ **Threat model documented**
- ✅ **API docs added**
- ✅ **Troubleshooting runbook**
- ✅ **Metrics exported**

### New Production Readiness Score
| Dimension | Before | After |
|-----------|--------|-------|
| Architecture | 7.5/10 | 7.5/10 |
| Code Quality | 3/10 | **7/10** |
| Testing | 5/10 | **6/10** |
| Security | 3/10 | **4/10** |
| Observability | 2/10 | **6/10** |
| Deployment | 1/10 | **2/10** |
| ML/AI | 2/10 | **6/10** |
| Documentation | 4/10 | **7/10** |
| **AVERAGE** | **3.3/10** | **5.8/10** |

**You'll jump from 4.5/10 to 5.8/10 (28% improvement)**

---

## SUCCESS CRITERIA (How to Know You're Done)

After 80 hours of focused work, verify:

```bash
# 1. All tests pass
./scripts/dev test
# Expected: 32 tests passing

# 2. No linting errors
./scripts/dev lint
# Expected: 0 errors

# 3. Inference works
python3 -c "from inference.engine import get_inference_engine; engine = get_inference_engine(); print('✓ Inference engine loaded')"
# Expected: ✓ Inference engine loaded

# 4. Models exist
ls training/models/
# Expected: keystroke_model.onnx, mouse_model.onnx, keystroke_scaler.pkl, mouse_scaler.pkl

# 5. Metrics exported
./scripts/dev metrics | grep keystroke_events_total
# Expected: keystroke_events_total 123

# 6. Documentation complete
grep -l "THREAT_MODEL\|TROUBLESHOOTING\|API" docs/*.md
# Expected: All files exist
```

---

## Common Pitfalls (Don't Do These)

❌ **Don't** skip type hints. Add them as you go, not at the end.  
❌ **Don't** use synthetic data to train. Collect real user data first.  
❌ **Don't** commit models to git. Store in `/opt/seclyzer/models/`.  
❌ **Don't** leave secrets in code. Use environment variables.  
❌ **Don't** ignore pre-commit hook failures. Fix and re-commit.  

---

## Questions You'll Have

**Q: What if I only have 50 keystroke samples?**  
A: Use the synthetic negative generator. Real data collection takes 2 weeks.

**Q: What if inference is slow (>1 second)?**  
A: Profile it. Likely culprit: ONNX model loading. Cache it.

**Q: What if tests fail?**  
A: Run with `-vv` for details: `pytest tests/ -vv`

**Q: Do I need to pay for Grafana?**  
A: No, use free Grafana Cloud or self-hosted.

---

## Time Estimate Verification

| Phase | Hours | Days |
|-------|-------|------|
| Week 1: Training pipeline | 16 | 2 |
| Week 1: Inference engine | 16 | 2 |
| Week 1: Integration | 8 | 1 |
| Week 2: Code quality | 16 | 2 |
| Week 2: Monitoring | 16 | 2 |
| Buffer (debugging, testing) | 8 | 1 |
| **TOTAL** | **80** | **10** |

**Realistic timeline:** 2 weeks at 10 hours/day, or 1 week at 14 hours/day, or 3 weeks part-time (5 hours/day).

Choose your pace. But don't spread it over 2 months—you'll lose context.
