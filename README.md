# SecLyzer

**Behavioral Biometric Authentication System**  
**Version:** 0.2.0 | **Status:** B- (Production Hardening Phase) | **License:** MIT

> Continuous authentication based on typing patterns, mouse behavior, and application usage.

---

## 🎯 What is SecLyzer?

SecLyzer is a behavioral biometric authentication system that learns your unique interaction patterns with your computer and uses them for continuous, transparent authentication. Instead of just passwords, it monitors:

- ⌨️ **Keystroke Dynamics** - How you type (timing, rhythm, pressure)
- 🖱️ **Mouse Behavior** - How you move and click
- 📱 **App Usage** - Which apps you use and when

### Key Features

- ✅ **Real-time Monitoring** - Continuous behavioral analysis
- ✅ **Machine Learning** - Adaptive models trained on your behavior
- ✅ **Local Processing** - All data stays on your machine
- ✅ **Production Hardening** - Logging, retry logic, validation, configuration management
- ✅ **Developer Tools** - Comprehensive management scripts and testing suite

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [Development](#-development)
- [Testing](#-testing)
- [Documentation](#-documentation)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🚀 Quick Start

### Prerequisites

- **OS:** Linux (Ubuntu 20.04+, Debian, Arch)
- **Python:** 3.8+
- **Rust:** 1.60+ (for building collectors)
- **Databases:** Redis, InfluxDB
- **Dependencies:** See `requirements_ml.txt`

### Installation (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourname/SecLyzer.git
cd SecLyzer

# 2. Run installer
chmod +x install.sh
./install.sh

# 3. Start services
./scripts/dev start

# 4. Verify
./scripts/dev status
```

---

## 🏗️ Architecture

SecLyzer follows a multi-stage pipeline:

```
┌─────────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────┐
│  Collectors │ -> │  Extractors  │ -> │  Training  │ -> │ Inference│
│   (Rust)    │    │   (Python)   │    │  (ML)      │    │  Engine  │
└─────────────┘    └──────────────┘    └────────────┘    └──────────┘
      ↓                    ↓                    ↓              ↓
    Redis              InfluxDB             SQLite         Redis
```

### Components

1. **Collectors (Rust)** - Low-level event capture
   - `keyboard_collector` - Captures keystrokes
   - `mouse_collector` - Tracks mouse movements
   - `app_monitor` - Monitors application switches

2. **Extractors (Python)** - Feature engineering
   - `keystroke_extractor.py` - Typing dynamics (dwell, flight, rhythm, errors)
   - `mouse_extractor.py` - Mouse movement, clicks, and scrolling behavior
   - `app_tracker.py` - App transitions and time-of-day usage patterns

3. **Training (Python)** - Machine learning
   - `KeystrokeModel` - Random Forest classifier
   - `MouseModel` -One-Class SVM
   - `AppModel` - Markov Chain

4. **Inference (Python)** - Real-time scoring
   - `InferenceEngine` - ONNX runtime inference
   - `TrustScorer` - Weighted fusion of modality scores

---

## 💿 Installation

### Option 1: Automated Install (Recommended)

```bash
./install.sh
```

This installs:
- Dependencies (Redis, InfluxDB, Python packages)
- Compiles Rust collectors
- Sets up databases
- Creates directory structure

### Option 2: Manual Install

See `docs/MANUAL_INSTALL.md` for step-by-step instructions.

### Option 3: Systemd Auto-Start

For production deployment with auto-start on boot:

```bash
sudo ./scripts/install_systemd.sh $USER
```

---

## 🎮 Usage

### Daily Workflow

```bash
# Start the system
./scripts/dev start

# Check status
./scripts/dev status

# View live logs
./scripts/dev logs

# Check data collection progress
./scripts/dev check-data
```

### Training Models

Once you have enough data (1-2 weeks of normal use):

```bash
# Check readiness
./scripts/dev check-data

# Train models
./scripts/dev train
```

## 👨‍💻 Development

### Developer Script

SecLyzer includes a comprehensive developer management script with 20+ commands:

```bash
./scripts/dev help
```

**Common Commands:**

```bash
# Service Management
./scripts/dev start          # Start all services
./scripts/dev stop           # Stop all services
./scripts/dev status         # Show detailed status

# Testing
./scripts/dev test           # Run test suite (36 tests)
./scripts/dev test-coverage  # Generate coverage report
./scripts/dev lint           # Run linters

# Debugging
./scripts/dev show-metrics   # Display system metrics
./scripts/dev debug-redis    # Monitor Redis events
./scripts/dev tail-json-logs # Parse JSON logs

# Utilities
./scripts/dev config         # Show configuration
./scripts/dev version        # Show version info
./scripts/dev backup         # Create backup
```

See `docs/CONTROL_SCRIPTS.md` for complete documentation.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| `docs/CONTROL_SCRIPTS.md` | Complete guide to seclyzer and dev scripts |
| `CHANGELOG.md` | All changes and releases |
| `NEXT_AGENT_HANDOVER.md` | System architecture and current state |

---

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check logs
./scripts/dev logs

# Verify dependencies
./scripts/dev check-health

# Restart services
./scripts/dev restart
```

### No Data Being Collected

```bash
# Verify collectors are running
./scripts/dev status

# Monitor Redis events
./scripts/dev debug-redis
# Then type/move mouse to see events
```

### Database Connection Errors

```bash
# Test Redis
redis-cli ping  # Should return PONG

# Test InfluxDB
curl http://localhost:8086/ping  # Should return 204

# Or use dev script
./scripts/dev debug-influx
```

See `docs/TROUBLESHOOTING.md` for more.

---

## 🤝 Contributing

Contributions welcome! Please read `CONTRIBUTING.md` first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing`)
3. Run checks (`./scripts/dev lint` and `./scripts/dev format`)
4. Commit your changes (`git commit -m 'Add feature'`)
5. Push to branch (`git push origin feature/amazing`)
6. Open a Pull Request

---

## 📝 License

MIT License - See `LICENSE` file for details.

---

## 🙏 Acknowledgments

- Built with Python, Rust, Redis, InfluxDB
- ML: scikit-learn, ONNX Runtime
- Data: Polars, NumPy

---

## 📞 Support

- **Issues:** GitHub Issues
- **Documentation:** `docs/` directory
- **Developer Console:** `./scripts/dev help`

---

**Made with ❤️ for secure, transparent authentication**
