# Developer Mode - Data Collection Behavior

## Summary

✅ **Collectors ALWAYS run** (even in dev mode)  
✅ **Data is tagged** with `dev_mode: true`  
✅ **Training excludes dev mode data** (by default)  
✅ **You can override** if you want to include it

---

## How It Works

### 1. Data Collection (Always Active)

When dev mode is ON:
- ✅ Keyboard collector still records keystrokes
- ✅ Mouse collector still tracks movement
- ✅ App monitor still logs switches
- ✅ Feature extraction still runs
- ✅ ML models still score your behavior

**Only the Decision Engine is bypassed** (no lockouts).

### 2. Data Tagging

All data collected during dev mode is tagged:

```json
{
  "timestamp": 1234567890,
  "event_type": "keystroke",
  "key": "KeyA",
  "dev_mode": true,
  "dev_mode_method": "magic_file",
  "dev_mode_activated_at": "2024-11-27T17:15:00"
}
```

### 3. Training Exclusion

When you train models (Phase 4), dev mode data is **automatically excluded**:

```python
# In training/train_keystroke.py
from common.developer_mode import get_developer_mode

# Load all data
all_data = load_features_from_database()

# Filter out dev mode data
training_data = all_data[all_data['dev_mode'] == False]

# Train on clean data only
model.fit(training_data)
```

---

## Use Cases

### Scenario 1: Pure Testing (Default)

**Goal:** Test SecLyzer without polluting training data

**Action:** Activate dev mode, test, deactivate

**Result:** 
- ✅ No lockouts during testing
- ✅ Data is tagged as `dev_mode: true`
- ✅ Training automatically excludes it

### Scenario 2: Adversarial Training

**Goal:** Train the model to recognize "not you" behavior

**Example:** You pretend to be someone else (hunt-and-peck typing, slow mouse)

**Action:** 
1. Activate dev mode
2. Type/move like an imposter
3. During training, INCLUDE dev mode data as **negative samples**

```python
# training/train_keystroke.py
negative_samples = all_data[all_data['dev_mode'] == True]
positive_samples = all_data[all_data['dev_mode'] == False]

# Train with both
model.fit(positive_samples, label=1)  # You
model.fit(negative_samples, label=0)  # Not you
```

### Scenario 3: Collect Training Data While Testing

**Goal:** Test feature extraction while collecting good data

**Action:**
1. DON'T activate dev mode
2. Type normally
3. If you get locked out, use dev mode temporarily to unlock

**Result:**
- ✅ Good data collected
- ⚠️ Temporary lockout (expected during training phase)

---

## Configuration

Control how dev mode data is handled in `config/dev_mode.yml`:

```yaml
data_collection:
  # Tag data collected during dev mode
  tag_data: true
  
  # Completely stop data collection in dev mode (not recommended)
  stop_collection: false
  
  # Training behavior
  exclude_from_training: true  # Default: exclude
  
  # Option to use dev mode data as negative samples
  use_as_negative_samples: false
```

---

## Recommendation

**Default behavior is perfect for you:**

1. ✅ Keep collectors running (always record)
2. ✅ Tag dev mode data
3. ✅ Exclude from training

This means:
- You can test freely without polluting your profile
- Data is still collected (for debugging)
- Training only uses your real behavior

**If you want to stop collection entirely**, set:
```yaml
data_collection:
  stop_collection: true
```

But I don't recommend this because:
- ❌ Can't collect training data while testing
- ❌ Can't see what features are being extracted
- ❌ Harder to debug

---

## Summary: What Happens in Dev Mode

| Component | Behavior |
|-----------|----------|
| Keyboard Collector | ✅ RUNS (records timing) |
| Mouse Collector | ✅ RUNS (records movement) |
| App Monitor | ✅ RUNS (records switches) |
| Feature Extraction | ✅ RUNS (calculates features) |
| ML Models | ✅ RUN (score behavior) |
| Data Tagging | ✅ Tags with `dev_mode: true` |
| **Decision Engine** | ❌ BYPASSED (always allow) |
| Training | ❌ Filters out dev mode data |

**Bottom line:** Everything works normally, you just can't get locked out.
