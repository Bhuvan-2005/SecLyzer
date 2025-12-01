# Privacy Overview for SecLyzer

SecLyzer is a local behavior analytics project. It is intended for **research, education, and personal experimentation**, not as a managed commercial product. This document explains at a high level what data SecLyzer may process and how you should treat that data.

## What Data Is Processed?

Depending on your configuration, SecLyzer may collect and process:

- **Keyboard behavior**
  - Key press/release timestamps
  - Event types (press/release)
  - Derived timing features (e.g., dwell, flight times, rhythm statistics)
  - **Goal:** store *features* and timing, not full text or passwords.

- **Mouse behavior**
  - Cursor movement events (positions, deltas)
  - Click and scroll events
  - Derived features (velocity, acceleration, jerk, click patterns, idle time)

- **Application usage**
  - Active window/application identifiers
  - App transition sequences and durations
  - Simple statistics about which apps are used and when

- **System metadata**
  - Timestamps
  - A local user identifier (e.g., `primary`)

> **Important:** Even without raw text, behavioral data can be sensitive. Treat all collected data as private and potentially identifying.

## Storage Backends

SecLyzer uses local storage components by default:

- **InfluxDB** for time-series feature data (keystroke, mouse, app features).
- **SQLite** for model metadata and configuration.
- **Log files** in `/var/log/seclyzer` for JSON logs and diagnostics.

All of these live on the local machine by default and are not meant to be exposed over the network.

## Intended Use

SecLyzer is designed primarily for:

- Personal research on behavioral biometrics
- Academic / portfolio demonstration
- Local experiments on your own workstation

It is **not** designed as a cloud service or multi-tenant system. Do not deploy it to environments where:

- Untrusted users can access the same machine or databases
- Logs and databases are publicly reachable from the internet

## Your Responsibilities

When using SecLyzer, you are responsible for:

1. **Legal and ethical use**
   - Only collect behavioral data from systems and users where you have clear permission.
   - Respect local laws and institutional policies on monitoring and data collection.

2. **Protecting stored data**
   - Restrict OS-level access to `/var/lib/seclyzer` and `/var/log/seclyzer`.
   - Consider full-disk or directory-level encryption.
   - Regularly review and rotate credentials (Redis, InfluxDB, etc.).

3. **Configuration choices**
   - Review `config/` files and environment variables before running in a real environment.
   - Decide how long to retain data in InfluxDB and SQLite.

## Data Removal

To remove collected data, you can:

- Use the provided helper scripts (e.g., to reset InfluxDB buckets) where available.
- Manually delete or rotate:
  - InfluxDB buckets associated with SecLyzer
  - The SQLite database file (typically `/var/lib/seclyzer/databases/seclyzer.db`)
  - Log files in `/var/log/seclyzer`

Be careful: deleting these files is irreversible and may break the system until reinitialized.

## Contributions and Changes

This document is intentionally high-level and may not cover every configuration. If you extend SecLyzer or change how data is stored/processed, please update this file to reflect:

- New data types collected
- New storage backends or remote endpoints
- Any changes that affect privacy expectations

## Contact

This is a personal/portfolio project. If you have questions or suggestions about privacy aspects of SecLyzer, please open an issue or contact the maintainer through the project repository.
