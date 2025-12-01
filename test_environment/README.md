# SecLyzer Rust Extractors - Test Environment

This directory contains Rust implementations of the Python extractors for production performance and robustness.

## Directory Structure

```
extractors_rs/
├── Cargo.toml                 # Workspace root
├── common/                    # Shared libraries (Redis, InfluxDB, config)
│   ├── src/
│   │   ├── lib.rs
│   │   ├── config.rs          # Configuration management
│   │   ├── redis_client.rs    # Redis pub/sub client
│   │   ├── influx_client.rs   # InfluxDB HTTP client
│   │   ├── models.rs          # Data structures
│   │   └── logger.rs          # Logging setup
│   └── Cargo.toml
├── keystroke_extractor/       # 140-feature keystroke dynamics
│   ├── src/
│   │   ├── main.rs            # Entry point
│   │   ├── lib.rs
│   │   ├── extractor.rs       # Event buffer and processor
│   │   └── features.rs        # Feature calculation logic
│   └── Cargo.toml
├── mouse_extractor/           # 38-feature mouse behavior (TBD)
├── app_tracker/               # App usage patterns (TBD)
└── tests/                     # Integration tests (TBD)
```

## Current Status

### ✅ Complete
- **common**: Shared infrastructure
  - Redis connection and pub/sub
  - InfluxDB HTTP client with line protocol
  - Configuration from environment variables
  - Data models and types
  
- **keystroke_extractor**: Core feature extraction
  - Keystroke event buffering (10K max)
  - 140-feature calculation:
    - Dwell times (8 features): mean, std, min, max, median, q25, q75, range
    - Flight times (8 features): same statistics
    - Digraphs (20 features): top 20 key-pair timings
    - Error patterns (4 features): backspace frequency, correction rate
    - Rhythm (8 features): consistency, burst/pause frequency, typing speed
    - Metadata (variable): dev_mode, total_keys
  - Redis pub/sub publishing
  - InfluxDB write capability

### 🚧 In Progress
- **mouse_extractor**: Movement/click/scroll features (38 total)
- **app_tracker**: Application usage patterns

### ⏳ Not Started
- Integration tests
- Production deployment scripts

## Building

### Prerequisites
```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install dependencies
# Ubuntu/Debian
sudo apt-get install build-essential
```

### Build All
```bash
cd /home/bhuvan/Documents/Projects/SecLyzer/test_environment/extractors_rs
cargo build --release
```

### Build Specific Extractor
```bash
# Keystroke only
cargo build --release -p keystroke_extractor

# Common library
cargo build --release -p common
```

## Configuration

Copy the `.env` file from the main SecLyzer project:

```bash
cp /home/bhuvan/Documents/Projects/SecLyzer/.env.example .env
```

Edit `.env` as needed:
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=                    # Leave empty if no password

INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your_token
INFLUX_ORG=seclyzer
INFLUX_BUCKET=behavioral_data

WINDOW_SECONDS=30
UPDATE_INTERVAL=5

SECLYZER_DEV_MODE=false
```

## Testing

### Run keystroke extractor in test mode
```bash
cd extractors_rs
cargo run --release -p keystroke_extractor
```

This will:
1. Load configuration from `.env`
2. Connect to Redis
3. Connect to InfluxDB
4. Wait for keystroke events on Redis channel `seclyzer:events`
5. Publish features to `seclyzer:features:keystroke`

### Manual Event Injection (Redis)
```bash
redis-cli

# Inject a keystroke press event
PUBLISH seclyzer:events '{"type":"keystroke","ts":1701423846000000,"key":"a","event":"press"}'

# Inject a keystroke release event
PUBLISH seclyzer:events '{"type":"keystroke","ts":1701423846050000,"key":"a","event":"release"}'
```

### Monitor Redis Pub/Sub
```bash
redis-cli
SUBSCRIBE seclyzer:features:keystroke
# Should see published features as JSON
```

### Verify InfluxDB Write
```bash
# Query InfluxDB (if configured)
curl -H "Authorization: Token YOUR_TOKEN" \
  'http://localhost:8086/api/v2/query?org=seclyzer' \
  -d 'from(bucket:"behavioral_data") |> range(start:-1h) |> filter(fn: (r) => r._measurement == "keystroke_features")'
```

## Performance Characteristics

Expected improvements over Python version:

| Metric | Python | Rust | Improvement |
|--------|--------|------|-------------|
| Memory usage | ~120MB | ~15-20MB | 80% reduction |
| CPU usage | ~1-2% | ~0.1-0.2% | 90% reduction |
| Startup time | ~2-3s | ~200-300ms | 85% reduction |
| Feature extraction latency | ~50ms | ~5-10ms | 80% reduction |

## Next Steps

1. **Complete mouse_extractor**: 38-feature mouse dynamics
2. **Complete app_tracker**: Application transition patterns
3. **Integration tests**: Unit + integration test suite
4. **Performance testing**: Load testing and benchmarks
5. **Merge to production**: After all tests pass

## Troubleshooting

### "Connection refused" on Redis
- Check Redis is running: `redis-cli ping`
- Verify `REDIS_HOST` and `REDIS_PORT` in `.env`

### "Failed to connect to InfluxDB"
- Check InfluxDB is running: `curl http://localhost:8086/api/v2/ready`
- Verify `INFLUX_TOKEN` is valid
- Check `INFLUX_BUCKET` exists in InfluxDB

### "Cannot find common module"
- Ensure you're in the workspace root: `/test_environment/extractors_rs/`
- Run `cargo build` before `cargo run`

## Architecture Notes

### Design Decisions

1. **Workspace Structure**: All extractors share `common` library for DRY
2. **Async/Await**: Tokio runtime for concurrent I/O (Redis, InfluxDB)
3. **Error Handling**: anyhow + custom error types for robust operations
4. **Logging**: tracing crate for structured logging
5. **Configuration**: Environment variables (12-factor app compliance)

### Thread Safety

- `AppContext` is `Arc` wrapped for thread-safe sharing
- Redis `ConnectionManager` is thread-safe by design
- Extractors are independent (no shared state between them)

### Feature Parity

All feature calculations are ported 1:1 from Python:
- Identical window/interval logic
- Same statistics functions (mean, std, percentile)
- Same thresholds (0-1000ms dwell, 0-2000ms flight, etc.)

## License

MIT - Same as SecLyzer
