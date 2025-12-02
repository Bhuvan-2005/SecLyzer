# Contributing to SecLyzer

Thank you for your interest in contributing to SecLyzer! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Be kind, constructive, and professional in all interactions.

---

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/SecLyzer.git
   cd SecLyzer
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/originalowner/SecLyzer.git
   ```

---

## Development Setup

### Prerequisites

- Linux (Ubuntu 20.04+ recommended)
- Python 3.12+
- Rust 1.60+
- Redis 6.0+
- InfluxDB 2.0+

### Installation

```bash
# Run the installer
./install.sh

# Verify installation
./scripts/dev check-health
./scripts/dev smoke-test
```

### Running Tests

```bash
# Run all tests
./scripts/dev test

# Run with coverage
./scripts/dev test-coverage

# Run fast tests only
./scripts/dev test-fast
```

---

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-model` - New features
- `fix/redis-connection` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/cleanup-extractors` - Code refactoring

### Commit Messages

Follow conventional commits:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat(inference): add score smoothing algorithm
fix(decision): correct threshold comparison
docs(readme): update installation instructions
```

---

## Testing

### Running Tests

```bash
# All tests
./scripts/dev test

# Specific test file
pytest tests/inference/test_inference_engine.py -v

# Specific test
pytest tests/inference/test_inference_engine.py::TestScoring -v
```

### Writing Tests

- Place tests in `tests/` directory
- Mirror the source structure
- Use pytest fixtures
- Aim for >80% coverage

Example:
```python
import pytest
from processing.inference.inference_engine import InferenceEngine

@pytest.fixture
def engine():
    return InferenceEngine()

def test_score_calculation(engine):
    score = engine.score_keystroke_features(features)
    assert 0 <= score <= 100
```

---

## Submitting Changes

### Pull Request Process

1. **Update your fork**:
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

2. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature
   ```

3. **Make changes** and commit

4. **Run checks**:
   ```bash
   ./scripts/dev lint
   ./scripts/dev test
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature
   ```

6. **Open a Pull Request** on GitHub

### PR Requirements

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated (if needed)
- [ ] Changelog updated (for significant changes)
- [ ] No merge conflicts

---

## Style Guidelines

### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use Black for formatting

```bash
# Format code
./scripts/dev format

# Check style
./scripts/dev lint
```

### Rust

- Follow Rust conventions
- Use `cargo fmt` for formatting
- Use `cargo clippy` for linting

### Documentation

- Use Markdown for docs
- Keep README.md up to date
- Document public APIs
- Include examples

---

## Reporting Issues

### Bug Reports

Include:
1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: How to trigger the bug
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Python version, etc.
6. **Logs**: Relevant log output

### Feature Requests

Include:
1. **Problem**: What problem does this solve?
2. **Solution**: Proposed solution
3. **Alternatives**: Other approaches considered
4. **Context**: Why is this important?

---

## Questions?

- Open an issue for questions
- Check existing issues first
- Be patient and respectful

---

Thank you for contributing to SecLyzer! 🎉
