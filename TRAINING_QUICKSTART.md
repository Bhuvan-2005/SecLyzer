# SecLyzer - Model Training Quick Start

**Get your behavioral biometric models trained in 5 minutes!**

---

## ⚡ Prerequisites

- SecLyzer installed and running
- Data collected for at least 2-3 days
- Virtual environment activated

---

## 🚀 Quick Start (3 Steps)

### Step 1: Check Your Data

```bash
cd ~/Documents/Projects/SecLyzer
source /home/bhuvan/Documents/Projects/venv/bin/activate
export PYTHONPATH=$PWD:$PYTHONPATH

python scripts/train_models.py --check
```

**Look for:**
- ✅ Green checkmarks = Ready to train
- ⚠️ Yellow warnings = Minimum met, more data recommended
- ❌ Red X = Not enough data, wait longer

### Step 2: Train All Models

```bash
python scripts/train_models.py --all
```

**Wait 30-60 seconds** while models train.

### Step 3: Verify Success

```bash
ls -lh data/models/
```

**You should see:**
- `keystroke_rf_*.pkl` and `*.onnx`
- `mouse_svm_*.pkl` and `*.onnx`
- `app_markov_*.json`

**Done!** Your models are trained and ready.

---

## 📊 What Gets Trained?

| Model | Features | Algorithm | Purpose |
|-------|----------|-----------|---------|
| **Keystroke** | 140 | Random Forest | Detect impostor typing |
| **Mouse** | 38 | One-Class SVM | Detect unusual mouse behavior |
| **App Usage** | N/A | Markov Chain | Learn app switching patterns |

---

## ⚙️ Common Options

### Use Less Data (Faster, Less Accurate)

```bash
python scripts/train_models.py --all --days 7
```

### Force Training (Not Recommended)

```bash
python scripts/train_models.py --all --force
```

### Train Specific Models

```bash
# Just keystroke
python scripts/train_models.py --keystroke

# Keystroke + mouse
python scripts/train_models.py --keystroke --mouse

# Just app usage
python scripts/train_models.py --app
```

---

## 🔍 Understanding the Output

### During Training

```
╔════════════════════════════════════════════════════════╗
║      SecLyzer - Model Training Orchestrator            ║
╚════════════════════════════════════════════════════════╝

📊 Checking Data Availability...

✅ Keystroke:    1234 samples
   Status: OPTIMAL
   Progress: 123.4% of recommended

✅ Mouse:        1876 samples  
   Status: OPTIMAL
   Progress: 125.1% of recommended

✅ App:           156 samples
   Status: READY
   Progress: 156.0% of recommended

============================================================
  TRAINING KEYSTROKE MODEL
============================================================

🤖 Training Random Forest Classifier...
   Samples: 1234
   Features: 140
   Positive: 1234 | Negative: 370

⚙️  Training with 50 trees...
✓ Training completed in 18.42 seconds

📈 Model Performance:
   Accuracy:  0.9234
   Precision: 0.9156
   Recall:    0.9345
   F1 Score:  0.9249

💾 Saved PKL model: data/models/keystroke_rf_v1.0.0_20251202_143022.pkl
💾 Saved ONNX model: data/models/keystroke_rf_v1.0.0_20251202_143022.onnx

============================================================
  TRAINING SUMMARY
============================================================

KEYSTROKE      : ✅ SUCCESS
MOUSE          : ✅ SUCCESS
APP_USAGE      : ✅ SUCCESS

📊 Overall: 3/3 models trained successfully

⏱️  Total training time: 45.67 seconds
```

### What the Metrics Mean

- **Accuracy:** Overall correctness (85-95% is good)
- **Precision:** How many predicted positives are correct (90%+ is excellent)
- **Recall:** How many actual positives were found (90%+ is excellent)
- **F1 Score:** Balance of precision and recall (90%+ is excellent)

---

## ❓ Troubleshooting

### "Insufficient data"

**Problem:**
```
❌ Insufficient data: 234 samples (need 500)
```

**Solutions:**
1. Wait 1-2 more days for data collection
2. Check extractors are running: `ps aux | grep extractor`
3. Use `--force` flag (not recommended for production)

### "Database connection error"

**Problem:**
```
❌ Failed to connect to InfluxDB
```

**Solutions:**
1. Check InfluxDB: `systemctl status influxdb`
2. Restart if needed: `sudo systemctl restart influxdb`
3. Test connection: `curl http://localhost:8086/ping`

### Low accuracy (<70%)

**Solutions:**
1. Collect more data (aim for 1000+ samples)
2. Use longer time window: `--days 30`
3. Exclude dev mode data (default behavior)
4. Re-train after collecting more data

---

## 📚 What's Next?

After training:

1. **Verify models were saved:**
   ```bash
   ls -lh data/models/
   sqlite3 /var/lib/seclyzer/databases/seclyzer.db \
     "SELECT model_type, accuracy, trained_at FROM models ORDER BY trained_at DESC;"
   ```

2. **Re-train periodically:**
   - Every 1-2 months
   - After significant behavior changes
   - To incorporate new data

3. **Wait for Phase 4:**
   - Inference engine (coming soon)
   - Real-time scoring
   - Integration with system authentication

---

## 📖 More Information

- **Detailed Guide:** See `docs/MODEL_TRAINING.md`
- **Architecture:** See `ARCHITECTURE.md`
- **Control Scripts:** See `docs/CONTROL_SCRIPTS.md`
- **Tests:** Run `pytest tests/models/ -v`

---

## 💡 Pro Tips

1. **Best Results:** Let system run for 1-2 weeks before first training
2. **Natural Usage:** Don't change your behavior during data collection
3. **Multiple Versions:** Old models aren't deleted, keep for comparison
4. **Backup Models:** Copy `data/models/` regularly
5. **Monitor Performance:** Track accuracy over time

---

**Need Help?** Check `docs/MODEL_TRAINING.md` for detailed troubleshooting.

**Ready to train?** Run: `python scripts/train_models.py --all`
