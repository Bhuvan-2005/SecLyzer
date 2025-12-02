# SecLyzer

<div align="center">

![Version](https://img.shields.io/badge/version-0.3.1-blue.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Tests](https://img.shields.io/badge/tests-178%20passing-brightgreen.svg)

**Behavioral Biometric Authentication System**

*Continuous authentication based on typing patterns, mouse behavior, and application usage.*

[Features](#-features) •
[Quick Start](#-quick-start) •
[Architecture](#-architecture) •
[Usage](#-usage) •
[Documentation](#-documentation)

</div>

---

## 🎯 What is SecLyzer?

SecLyzer is a **behavioral biometric authentication system** that learns your unique interaction patterns with your computer and uses them for continuous, transparent authentication. Instead of relying solely on passwords, it monitors:

| Modality | What It Tracks | Features |
|----------|---------------|----------|
| ⌨️ **Keystroke Dynamics** | How you type | Timing, rhythm, dwell time, flight time, error patterns |
| 🖱️ **Mouse Behavior** | How you move and click | Velocity, acceleration, curvature, click patterns |
| 📱 **App Usage** | Which apps you use | Transition patterns, time-of-day preferences |

### Why Behavioral Biometrics?

- **Continuous**: Authentication happens constantly, not just at login
- **Transparent**: No user interaction required
- **Adaptive**: Models learn and adapt to your behavior
- **Privacy-First**: All processing happens locally on your machine

---

## ✨ Features

### Core Capabilities
- ✅ **Real-time Monitoring** - Continuous behavioral analysis every 5 seconds
- ✅ **Machine Learning** - Adaptive models trained on your unique behavior
- ✅ **Local Processing** - All data stays on your machine (no cloud)
- ✅ **Decoupled Architecture** - Modular engines that can be enabled/disabled independently

### Security Features
- 🔒 **4-State Authentication** - Normal → Monitoring → Restricted → Lockdown
- 🔒 **Confirmation Logic** - Requires 3 consecutive anomalies before action
- 🔒 **Developer Mode** - Bypass for testing without compromising security
- 🔒 **Audit Logging** - All decisions logged for forensics

### Developer Experience
- 🛠️ **Comprehensive CLI** - 30+ commands for management and debugging
- 🛠️ **178 Unit Tests** - Full test coverage
- 🛠️ **Structured Logging** - JSON logs with correlation IDs
- 🛠️ **Hot Reload** - Reload models without restart

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [Model Training](#-model-training)
- [Authentication States](#-authentication-states)
- [Configuration](#-configuration)
- [Development](#-development)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Security & Privacy](#-security--privacy)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **OS** | Linux (Ubuntu 20.04+) | Primary platform |
| **Python** | 3.12+ | Core runtime |
| **Rust** | 1.60+ | Collectors |
| **Redis** | 6.0+ | Message queue |
| **InfluxDB** | 2.0+ | Time-series storage |

### Installation (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/SecLyzer.git
cd SecLyzer

# 2. Run installer
chmod +x install.sh
./install.sh

# 3. Start data collection
./scripts/seclyzer start
./scripts/seclyzer extractors

# 4. Verify installation
./scripts/seclyzer status
```

### Typical Workflow

```bash
# Phase 1: Data Collection (1-2 weeks)
./scripts/seclyzer start           # Start collectors
./scripts/seclyzer extractors      # Start feature extraction
./scripts/seclyzer status          # Monitor progress

# Phase 2: Model Training
./scripts/seclyzer train --check   # Check data readiness
./scripts/seclyzer train --all     # Train all models

# Phase 3: Authentication
./scripts/seclyzer auth            # Start full protection
# OR
./scripts/seclyzer auth --no-locking  # Scores only (for testing)
```

---

## 🏗️ Architecture

SecLyzer follows a **multi-stage pipeline** with **decoupled engines**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SecLyzer Architecture                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────────────┐  │
│  │ Collectors│───▶│ Extractors│───▶│  Training │───▶│ Authentication    │  │
│  │  (Rust)   │    │ (Python)  │    │   (ML)    │    │    Pipeline       │  │
│  └───────────┘    └───────────┘    └───────────┘    │                   │  │
│       │                │                │           │  ┌─────────────┐  │  │
│       ▼                ▼                ▼           │  │  Inference  │  │  │
│    Redis           InfluxDB          SQLite        │  │   Engine    │  │  │
│                                                     │  └──────┬──────┘  │  │
│                                                     │         │         │  │
│                                                     │         ▼         │  │
│                                                     │  ┌─────────────┐  │  │
│                                                     │  │  Decision   │  │  │
│                                                     │  │   Engine    │  │  │
│                                                     │  └──────┬──────┘  │  │
│                                                     │         │         │  │
│                                                     │         ▼         │  │
│                                                     │  ┌─────────────┐  │  │
│                                                     │  │  Locking    │  │  │
│                                                     │  │  Engine     │  │  │
│                                                     │  │ (Optional)  │  │  │
│                                                     │  └─────────────┘  │  │
│                                                     └───────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Overview

| Layer | Component | Language | Description |
|-------|-----------|----------|-------------|
| **Collection** | `keyboard_collector` | Rust | Captures keystrokes with microsecond precision |
| **Collection** | `mouse_collector` | Rust | Tracks mouse movements at 50Hz |
| **Collection** | `app_monitor` | Rust | Monitors active application switches |
| **Extraction** | `keystroke_extractor` | Python | Extracts 140 typing features |
| **Extraction** | `mouse_extractor` | Python | Extracts 38 mouse features |
| **Extraction** | `app_tracker` | Python | Builds transition matrices |
| **Training** | `train_keystroke` | Python | Random Forest classifier |
| **Training** | `train_mouse` | Python | One-Class SVM |
| **Training** | `train_app_usage` | Python | Markov Chain model |
| **Inference** | `InferenceEngine` | Python | Real-time scoring with fusion |
| **Decision** | `DecisionEngine` | Python | 4-state authentication FSM |
| **Action** | `LockingEngine` | Python | Screen lock & notifications |

### Data Flow

```
Raw Events → Redis → Feature Extraction → InfluxDB → ML Inference → Decision → Action
     │                      │                              │            │
     │                      │                              │            │
  keyboard              keystroke                      confidence    screen
  mouse                 mouse                          scores        lock
  app                   app                                          notify
```

---

## 💿 Installation

### Option 1: Fully Automated (Recommended)

```bash
# Clone and install with one command
git clone https://github.com/yourusername/SecLyzer.git
cd SecLyzer
sudo ./install.sh --auto
```

This will:
- Install all dependencies (Redis, InfluxDB, Python packages)
- Build Rust collectors
- Set up databases
- Create systemd services
- Generate admin password (displayed at end)

### Option 2: Interactive Install

```bash
sudo ./install.sh
```

Prompts for customization of paths, passwords, and options.

### Option 3: Custom Installation

```bash
# With environment variables
sudo SECLYZER_PASSWORD=mypassword \
     SECLYZER_INSTALL_DIR=/opt/seclyzer \
     ./install.sh --auto

# Skip certain components
sudo ./install.sh --auto --no-redis      # If Redis already installed
sudo ./install.sh --auto --no-influxdb   # If InfluxDB already installed
sudo ./install.sh --auto --no-autostart  # Don't enable systemd services
```

### Installation Options

| Option | Description |
|--------|-------------|
| `--auto` | Fully automated, no prompts |
| `--no-redis` | Skip Redis installation |
| `--no-influxdb` | Skip InfluxDB installation |
| `--no-autostart` | Don't enable systemd auto-start |
| `--skip-build` | Skip building Rust collectors |

### Uninstallation

```bash
# Interactive uninstall
sudo /opt/seclyzer/uninstall.sh

# Automated uninstall (keeps data)
sudo /opt/seclyzer/uninstall.sh --auto

# Complete removal (removes all data)
sudo /opt/seclyzer/uninstall.sh --auto --purge

# With password from environment
sudo SECLYZER_PASSWORD=xxx /opt/seclyzer/uninstall.sh --auto --purge
```

---

## 🎮 Usage

### Control Script (`seclyzer`)

The main control interface for SecLyzer:

```bash
./scripts/seclyzer <command> [options]
```

#### Service Management

| Command | Description |
|---------|-------------|
| `start` | Start databases and collectors |
| `extractors` | Start feature extractors |
| `auth` | Start authentication engine (full protection) |
| `auth --no-locking` | Start without locking (scores only) |
| `restart` | Restart all services |
| `stop-extractors` | Stop feature extractors |
| `stop-auth` | Stop authentication engine |
| `stop-all` | Stop ALL services (requires password) |
| `status` | Show status of all components |
| `resources` | Show CPU/memory usage |

#### Model Training

| Command | Description |
|---------|-------------|
| `train --all` | Train all models |
| `train --keystroke` | Train keystroke model only |
| `train --mouse` | Train mouse model only |
| `train --app` | Train app usage model only |
| `train --check` | Check training data availability |
| `train --force` | Force training with insufficient data |
| `train --days N` | Use N days of historical data |

#### Authentication Control

| Command | Description |
|---------|-------------|
| `disable` | Disable authentication (developer mode) |
| `enable` | Re-enable authentication |
| `reload` | Hot-reload trained models |

#### Monitoring

| Command | Description |
|---------|-------------|
| `logs [component]` | View logs (all, auth, keystroke, mouse, app) |
| `version` | Show version information |

### Developer Script (`dev`)

Advanced management for developers:

```bash
./scripts/dev <command>
```

#### Key Commands

```bash
# Testing
./scripts/dev test              # Run all 178 tests
./scripts/dev test-coverage     # Generate coverage report
./scripts/dev test-fast         # Run tests without slow markers

# Debugging
./scripts/dev auth-start-no-lock  # Start without locking
./scripts/dev auth-scores         # Monitor confidence scores
./scripts/dev debug-decisions     # Monitor state changes
./scripts/dev debug-redis         # Monitor Redis events

# Utilities
./scripts/dev check-health      # Verify dependencies
./scripts/dev smoke-test        # Quick system test
./scripts/dev clean-pycache     # Remove __pycache__
./scripts/dev clean-models      # Remove trained models
```

---

## 🧠 Model Training

### Training Requirements

| Model | Minimum | Recommended | Collection Time |
|-------|---------|-------------|-----------------|
| Keystroke | 500 samples | 1000+ samples | 2-3 days |
| Mouse | 800 samples | 1500+ samples | 3-4 days |
| App Usage | 50 transitions | 100+ transitions | 1-2 days |

### Training Process

```bash
# 1. Check data readiness
./scripts/seclyzer train --check

# 2. Train all models
./scripts/seclyzer train --all

# 3. Verify models
ls -la data/models/
```

### Model Details

| Model | Algorithm | Features | Output |
|-------|-----------|----------|--------|
| **Keystroke** | Random Forest | 140 dimensions | PKL + ONNX |
| **Mouse** | One-Class SVM | 38 dimensions | PKL + ONNX |
| **App Usage** | Markov Chain | Transition matrix | JSON |

### Performance Optimizations

- Reduced tree count (50 vs 100) for Random Forest
- Limited SVM cache (500MB)
- Efficient data handling with Polars
- Parallel processing where possible
- **No GPU required**

---

## 🔐 Authentication States

SecLyzer uses a **4-state finite state machine**:

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐
│  NORMAL  │───▶│MONITORING│───▶│ RESTRICTED │───▶│ LOCKDOWN │
│  ≥70%    │    │  ≥50%    │    │   ≥35%     │    │  <35%    │
└──────────┘    └──────────┘    └────────────┘    └──────────┘
     ▲               │                │                │
     │               │                │                │
     └───────────────┴────────────────┴────────────────┘
                    (Immediate recovery on high score)
```

| State | Threshold | Action | Description |
|-------|-----------|--------|-------------|
| **NORMAL** | ≥70% | Allow | Full access, silent monitoring |
| **MONITORING** | ≥50% | Allow + Log | Enhanced logging, medium confidence |
| **RESTRICTED** | ≥35% | Restrict | Limited access, low confidence |
| **LOCKDOWN** | <35% | Lock Screen | Very low confidence, require re-auth |

### Key Behaviors

- **Degradation**: Requires 3 consecutive low scores before state change
- **Recovery**: High score immediately restores NORMAL state
- **Developer Mode**: Bypasses all authentication (for testing)

---

## ⚙️ Configuration

### Environment Variables

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password

# InfluxDB
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your_token
INFLUX_ORG=seclyzer
INFLUX_BUCKET=seclyzer

# SecLyzer
SECLYZER_LOG_LEVEL=INFO
SECLYZER_DEV_MODE=0
```

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (secrets) |
| `config/config.yaml` | Main configuration |
| `config/dev_mode.yml` | Developer mode settings |

---

## 👨‍💻 Development

### Project Structure

```
SecLyzer/
├── collectors/              # Rust collectors
│   ├── keyboard_collector/
│   ├── mouse_collector/
│   └── app_monitor/
├── processing/              # Python processing
│   ├── extractors/          # Feature extraction
│   ├── models/              # ML training
│   ├── inference/           # Real-time inference
│   ├── decision/            # Decision engine
│   └── actions/             # System actions (locking)
├── storage/                 # Database wrappers
├── common/                  # Shared utilities
├── daemon/                  # Main daemon
├── scripts/                 # Control scripts
├── tests/                   # Test suite (178 tests)
├── config/                  # Configuration
├── data/                    # Runtime data (gitignored)
│   ├── models/              # Trained models
│   ├── databases/           # SQLite
│   └── logs/                # Log files
└── docs/                    # Documentation
```

### Code Quality

```bash
# Format code
./scripts/dev format

# Run linters
./scripts/dev lint

# Type checking
mypy --ignore-missing-imports .
```

---

## 🧪 Testing

### Test Suite

```bash
# Run all tests
./scripts/dev test

# Run with coverage
./scripts/dev test-coverage

# Run fast tests only
./scripts/dev test-fast
```

### Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| Inference Engine | 22 | ✅ |
| Decision Engine | 28 | ✅ |
| Locking Engine | 24 | ✅ |
| Feature Extractors | 20 | ✅ |
| Model Training | 49 | ✅ |
| Storage | 7 | ✅ |
| Common | 12 | ✅ |
| Integration | 5 | ✅ |
| **Total** | **178** | ✅ |

---

## 🐛 Troubleshooting

### Common Issues

#### Services Not Starting

```bash
./scripts/dev check-health    # Verify dependencies
./scripts/dev logs            # Check logs
./scripts/dev restart         # Restart services
```

#### No Data Being Collected

```bash
./scripts/seclyzer status     # Check collector status
./scripts/dev debug-redis     # Monitor Redis events
```

#### Database Connection Errors

```bash
redis-cli ping                # Test Redis
curl http://localhost:8086/ping  # Test InfluxDB
./scripts/dev debug-influx    # Test InfluxDB client
```

#### Low Confidence Scores

```bash
./scripts/seclyzer train --check  # Check training data
./scripts/seclyzer train --all    # Retrain models
```

---

## 🔐 Security & Privacy

### Security Model

- **Local Processing**: All data stays on your machine
- **No Cloud**: No external API calls or data transmission
- **Encrypted Storage**: Databases can be encrypted with LUKS
- **Audit Trail**: All decisions logged for forensics

### Privacy Considerations

- **No Raw Text**: Only timing data stored, not actual keystrokes
- **Hashed Identifiers**: Window titles and app names hashed
- **Configurable Retention**: Data automatically deleted after 30 days

### Files

- `SECURITY.md` - Threat model and hardening guidelines
- `PRIVACY.md` - Data collection and storage policies

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Run tests (`./scripts/dev test`)
4. Run linters (`./scripts/dev lint`)
5. Commit changes (`git commit -m 'Add feature'`)
6. Push to branch (`git push origin feature/amazing`)
7. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/SecLyzer.git
cd SecLyzer

# Install in development mode
./install.sh

# Run tests
./scripts/dev test

# Make changes and test
./scripts/dev lint
./scripts/dev format
```

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and design |
| [CHANGELOG.md](CHANGELOG.md) | Version history and changes |
| [SECURITY.md](SECURITY.md) | Security model and guidelines |
| [PRIVACY.md](PRIVACY.md) | Privacy policy and data handling |
| [docs/CONTROL_SCRIPTS.md](docs/CONTROL_SCRIPTS.md) | CLI reference |

---

## 🙏 Acknowledgments

Built with:
- **Languages**: Python 3.12+, Rust
- **Databases**: Redis, InfluxDB, SQLite
- **ML**: scikit-learn, ONNX Runtime
- **Data**: Polars, NumPy

---

<div align="center">

**Made with ❤️ for secure, transparent authentication**

[Report Bug](https://github.com/yourusername/SecLyzer/issues) •
[Request Feature](https://github.com/yourusername/SecLyzer/issues)

</div>
