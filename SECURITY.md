# Security Policy for SecLyzer

## Scope

SecLyzer is a local behavior analytics system that collects keystroke, mouse, and application activity metadata to build user behavior models. It is designed primarily for research and educational use, not as a hardened enterprise product.

This document explains:
- What kinds of data SecLyzer processes
- Security assumptions and non-goals
- Recommended deployment practices

## Data Collected

SecLyzer is designed **not** to store raw sensitive content such as full keystroke text. Instead, it focuses on **timing and behavioral features**.

Depending on configuration, SecLyzer may process and store:

- **Keyboard behavior**
  - Timestamps of key press/release events
  - Derived features (dwell time, flight time, rhythm statistics)
  - No plaintext passwords or full text content are intended to be stored.

- **Mouse behavior**
  - Movement, click, and scroll events
  - Derived features (velocity, acceleration, click patterns, idle time)

- **Application usage**
  - Active window/application identifiers (e.g., window title or application name)
  - Transition statistics and usage durations

- **System metadata**
  - Timestamps referencing local time
  - Anonymous user identifier (e.g., `primary`)

### Sensitive Information

While SecLyzer avoids storing raw text, **timing and application metadata may still be sensitive**, especially when combined with other data. Treat all collected data as potentially sensitive behavioral telemetry.

## Trust Model & Assumptions

SecLyzer assumes:

- It is installed and run on a **single-user Linux workstation** under a trusted administrator account.
- Redis, InfluxDB, and SQLite are **bound to localhost** and not exposed to untrusted networks.
- The machine itself is not fully compromised (i.e., no root-level attacker already present).

Non-goals in the current snapshot:

- Protection against a fully compromised host or a malicious root user.
- End-to-end encryption or multi-tenant isolation.
- Remote administration and access control.

## Recommended Hardening Steps

If you use SecLyzer beyond local experimentation:

1. **Limit access to data directories**
   - Ensure `/var/lib/seclyzer` and `/var/log/seclyzer` are owned by a dedicated service user with restrictive permissions.
   - Use full-disk or partition-level encryption if the machine stores sensitive data.

2. **Keep services local-only**
   - Run Redis and InfluxDB bound to `127.0.0.1` only.
   - Avoid exposing these services over the network unless you understand and configure proper auth/TLS.

3. **Manage secrets carefully**
   - Do not commit real tokens or passwords to git.
   - Use `.env` files, `/etc/seclyzer/*`, or environment variables with correct file permissions.
   - Rotate any secrets that were ever checked into version control.

4. **Monitor dependencies**
   - Periodically run tools like `pip-audit` and `cargo audit` to check for known vulnerabilities.
   - Keep Python and Rust dependencies reasonably up to date.

5. **Review developer mode usage**
   - Developer-mode and debug features are intended for local testing.
   - Avoid enabling them on production-like machines or for untrusted users.

## Reporting Security Issues

This project is currently maintained as a personal/portfolio project. If you discover a security issue:

- Please open a **private issue or contact the maintainer directly**, rather than posting exploit details publicly.
- Provide:
  - A description of the issue
  - Steps to reproduce
  - The environment (OS, Python/Rust versions)

The maintainer will aim to reproduce and address issues on a best-effort basis.

## Disclaimer

SecLyzer is provided **as-is**, without any warranty or guarantee of fitness for production security use. It is intended for learning, experimentation, and demonstration of behavioral analytics concepts.
