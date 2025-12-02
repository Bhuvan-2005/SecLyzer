# Phase 2 Testing Guide - Feature Extraction

## Prerequisites
- Phase 1 collectors running
- Redis running
- InfluxDB and SQLite installed

## Step 1: Setup Databases

### InfluxDB Setup

```bash
cd ~/SecLyzer
sudo ./scripts/setup_influxdb.sh
```

**Save the password shown!** You'll need it to access the UI.

### SQLite Setup

```bash
sudo ./scripts/setup_sqlite.sh
```

Verify database:
```bash
sqlite3 /var/lib/seclyzer/databases/seclyzer.db "SELECT * FROM user_profile;"
```

## Step 2: Install Python Dependencies

```bash
source ~/.seclyzer-venv/bin/activate
pip install polars influxdb-client pyyaml numpy
```

## Step 3: Start Feature Extractors

### Terminal 1: Keystroke Extractor
```bash
source ~/.seclyzer-venv/bin/activate
cd ~/SecLyzer
python3 processing/extractors/keystroke_extractor.py
```

Expected output:
```
[Keystroke Extractor] Starting...
[Keystroke Extractor] Saved features | Dev mode: False
```

### Terminal 2: Mouse Extractor
```bash
source ~/.seclyzer-venv/bin/activate
cd ~/SecLyzer
python3 processing/extractors/mouse_extractor.py
```

### Terminal 3: App Tracker
```bash
source ~/.seclyzer-venv/bin/activate
cd ~/SecLyzer
python3 processing/extractors/app_tracker.py
```

## Step 4: Verify Data Collection

### Check InfluxDB

Access UI: http://localhost:8086

Login with credentials from setup script.

Navigate to: **Data Explorer** → Select bucket `behavioral_data`

You should see:
- `keystroke_features` (updates every 5 seconds)
- `mouse_features` (updates every 5 seconds)
- `app_transitions` (when you switch apps)

### Check SQLite

```bash
sqlite3 /var/lib/seclyzer/databases/seclyzer.db

-- View audit log
SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 10;

-- View models (will be empty until Phase 4)
SELECT * FROM models;

-- View config
SELECT * FROM config;

.quit
```

## Step 5: Test Feature Quality

### Keystroke Features

Type for 30 seconds, then check:

```bash
influx query -o seclyzer -t <YOUR_TOKEN> '
from(bucket:"behavioral_data")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "keystroke_features")
  |> last()
'
```

Should show ~140 fields like:
- `dwell_mean`, `dwell_std`, `dwell_min`, etc.
- `flight_mean`, `flight_std`, etc.
- `digraph_0_mean` through `digraph_19_mean`
- `typing_speed_wpm`, `rhythm_consistency`, etc.

### Mouse Features

Move mouse and click for 30 seconds:

```bash
influx query -o seclyzer -t <YOUR_TOKEN> '
from(bucket:"behavioral_data")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "mouse_features")
  |> last()
'
```

Should show ~38 fields like:
- `move_0` through `move_19` (velocity, acceleration, curvature)
- `click_0` through `click_9` (click patterns)
- `scroll_0` through `scroll_7` (scroll behavior)

### App Usage

Switch between apps a few times, then:

```bash
sqlite3 /var/lib/seclyzer/databases/seclyzer.db

SELECT value FROM config WHERE key='app_patterns';
```

Should show JSON with:
- transition_matrix (app switch probabilities)
- time_preferences (when you use each app)
- usage_stats (most used apps, etc.)

## Step 6: Test Developer Mode Integration

### Activate Dev Mode

```bash
touch /tmp/.seclyzer_dev_mode
```

### Verify Tagging

Type something, then check InfluxDB:

```bash
influx query -o seclyzer -t <YOUR_TOKEN> '
from(bucket:"behavioral_data")
  |> range(start: -1m)
  |> filter(fn: (r) => r._measurement == "keystroke_features")
  |> filter(fn: (r) => r._field == "dev_mode")
  |> last()
'
```

Should show `dev_mode=true`.

### Deactivate Dev Mode

```bash
rm /tmp/.seclyzer_dev_mode
```

## Troubleshooting

### "InfluxDB connection failed"

```bash
sudo systemctl status influxdb
sudo systemctl start influxdb
```

### "Redis connection failed"

```bash
sudo systemctl status redis-server
sudo systemctl start redis-server
```

### "No features being saved"

1. Check collectors are running (Phase 1)
2. Check extractors show no errors
3. Verify Redis has events: `redis-cli SUBSCRIBE seclyzer:events`
4. Check InfluxDB token in `/etc/seclyzer/influxdb_token`

### "Import errors"

Make sure you're in venv:
```bash
source ~/.seclyzer-venv/bin/activate
pip install -r requirements.txt  # If we create one
```

## Success Criteria

- [ ] InfluxDB running and accessible
- [ ] SQLite database created with schema
- [ ] Keystroke extractor saves features every 5 seconds
- [ ] Mouse extractor saves features every 5 seconds  
- [ ] App tracker records transitions
- [ ] Features visible in InfluxDB UI
- [ ] Dev mode properly tags data
- [ ] No Python errors in extractors

## Performance Check

### CPU Usage

```bash
top -b -n 1 | grep python
```

Should show **<3% CPU** per extractor.

### Memory Usage

```bash
ps aux | grep "python.*extractor"
```

Should show **<100 MB RAM** per extractor.

### InfluxDB Memory

```bash
influx query -o seclyzer -t <YOUR_TOKEN> '
buckets()
  |> filter(fn: (r) => r.name == "behavioral_data")
'
```

Check storage size, should grow slowly (~1-2 MB/hour with normal use).

## Next Steps

Once all tests pass:
1. Let extractors run for a few hours to collect data
2. Verify data accumulates in InfluxDB
3. Report back for Phase 3 (Model Training)

Phase 2 complete when you have consistent feature extraction running!
