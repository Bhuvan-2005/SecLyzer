# Cascade Agent Context – SecLyzer

**Last Updated:** 2025-12-01 19:50 IST  
**Agent:** Cascade (local coding assistant)  
**Scope:** SecLyzer Phase-3 snapshot + Python 3.12 fixes + tests + dev tooling

---

## 1. Purpose of This File

This document is a **profile-independent context anchor** for any future agent (including Cascade) working on SecLyzer in this repo.

It captures:

- **Current technical state** of the project (as of 2025-12-01)
- **Key workflows/commands** you should use instead of ad-hoc scripts
- **Where the rest of the deep context lives** under `.warp-local/`
- **What this agent (Cascade) already changed**

Use this as a high-level entrypoint, then jump into the other `.warp-local` docs for deep details.

---

## 2. Project State (Today)

- **Stack:**
  - Rust collectors (`collectors/*_collector`, `app_monitor`) → Redis pub/sub
  - Python extractors (`processing/extractors/`) using Polars/NumPy
  - Storage: InfluxDB (time-series) + SQLite (metadata)
  - Control scripts: `scripts/dev`, `scripts/seclyzer`
- **Tests:**
  - `tests/` package with **32 passing tests**:
    - `tests/common/` – config, logging, retry, developer_mode, validators
    - `tests/storage/` – SQLite wrapper + InfluxDB wrapper (mocked)
    - `tests/extractors/` – keystroke, mouse, app_tracker
    - `tests/integration/` – feature pipeline, CLI smoke tests
- **Python 3.12+ compatibility:**
  - Replaced deprecated `datetime.utcnow()` / `utcfromtimestamp()` usages with:
    - `datetime.now(timezone.utc)`
    - `datetime.fromtimestamp(ts, tz=timezone.utc)`
  - Added explicit datetime adapters for SQLite in `storage/database.py`.
- **Status:**
  - Architecture + feature extraction + storage are solid.
  - Still **no training/inference engine implemented** – system is a high-quality data logger.

For the longer, opinionated assessment and roadmap, see:

- `.warp-local/CONTEXT_SNAPSHOT.md`
- `.warp-local/PRODUCTION_READINESS_AUDIT.md`
- `.warp-local/SPRINT_2WEEKS.md`

---

## 3. Canonical Commands & Workflows

### 3.1 Dev/Test Workflow

From project root: `/home/bhuvan/Documents/Projects/SecLyzer`

```bash
# Activate venv
source /home/bhuvan/Documents/Projects/venv/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"

# Run tests
./scripts/dev test

# Run tests with coverage (requires pytest-cov installed)
./scripts/dev test-coverage
```

Smoke tests already verify:

- `./scripts/dev help` runs and prints the Developer Console help text.
- `./scripts/seclyzer help` runs and prints the Control Script help text.

### 3.2 Git Backup Workflow (NEW)

To snapshot your current work to a **timestamped backup branch** on `origin`:

```bash
cd /home/bhuvan/Documents/Projects/SecLyzer
./scripts/dev backup-git
```

What this does:

1. Verifies you are in a git repo and that `git` exists.
2. Checks for local changes; if working tree is clean, it exits.
3. Stages all changes: `git add -A`.
4. Creates a commit: `git commit -m "Automated backup YYYYMMDD-HHMMSS"`.
5. Creates a branch from the current branch:
   - `backup/<current_branch>-YYYYMMDD-HHMMSS`
6. Pushes that branch to `origin` and sets upstream.

Use this whenever you want a **safe remote snapshot** before large refactors. You can review and merge those backup branches into `master` manually on GitHub.

---

## 4. `.warp-local` Knowledge Base

The persistent context for this project is under:

```bash
/home/bhuvan/Documents/Projects/SecLyzer/.warp-local/
```

Key files (see them for deep detail):

- `00_START_HERE.md` – overview of the persistence system and how to verify it.
- `README.md` – navigation + reading order.
- `CONTEXT_SNAPSHOT.md` – 5-minute summary of what SecLyzer is and current readiness.
- `PRODUCTION_READINESS_AUDIT.md` – brutally honest 4.5/10 rating and gap analysis.
- `SPRINT_2WEEKS.md` – 80-hour plan to get from 4.5/10 → ~5.8/10.
- `DEEP_CODE_ANALYSIS.md` – line-by-line patterns and lessons from the code.
- `CODEBASE_AUDIT.md` – file inventory and data flows.
- `INVENTORY.md` – what exists, how big it is, and how to read it.
- `verify_context.sh` – script to sanity-check that this context still exists and is not in git.

This file (`AGENT_CASCADE_CONTEXT.md`) is an additional **agent-focused index** – it doesn’t replace the others.

---

## 5. What Cascade Has Already Done

Changes driven by this agent (in addition to previous work reflected in the other docs):

- **Testing**
  - Created a structured `tests/` package with unit + integration tests.
  - Ensured tests run cleanly in the venv via `./scripts/dev test`.
  - Added CLI smoke tests for `./scripts/dev` and `./scripts/seclyzer`.
  - **Verified:** All 32 tests pass (0 failures).

- **Python 3.12 compatibility**
  - Updated datetime usage to timezone-aware UTC where deprecations occurred.
  - Added custom datetime adapters for SQLite to satisfy Python 3.12 behaviour.
  - **Verified:** All extractors use `datetime.now(timezone.utc)` and `datetime.fromtimestamp(ts, tz=timezone.utc)`.

- **Developer tooling**
  - Implemented `backup-git` in `scripts/dev` to automate safe backup branches.
  - **Verified:** Command works and creates timestamped backup branches.

- **Warp context integration**
  - Read all `.warp-local/*.md` docs and synchronized them with:
    - The existence of the new test suite (32 tests, not 36).
    - The presence of `backup-git` in `scripts/dev`.
    - The Python 3.12 compatibility changes.

- **Full repository audit (2025-12-01)**
  - Audited all 50+ files in the repository.
  - Verified all claims in documentation against actual code.
  - Corrected 3 false claims (test count, Python version, planned vs. implemented modules).
  - Created comprehensive audit report: `.warp-local/AUDIT_REPORT_20251201.md`.
  - **Result:** All documentation is now truthful and accurate.

If you change any of these areas significantly (new tests, new scripts, Python version jump, etc.), you should:

1. Update `CHANGELOG.md` with a new section.
2. Update this file plus at least `CONTEXT_SNAPSHOT.md` and `CODEBASE_AUDIT.md`.

---

## 6. How a Future Agent Should Start

1. **Confirm environment:**
   - `python3 --version` (expect 3.12+)
   - `source /home/bhuvan/Documents/Projects/venv/bin/activate`
2. **Read minimal context (≤10 minutes):**
   - `.warp-local/CONTEXT_SNAPSHOT.md`
   - This file: `.warp-local/AGENT_CASCADE_CONTEXT.md`
3. **Run tests:**
   - `./scripts/dev test`
4. **If making risky changes, create a backup branch:**
   - `./scripts/dev backup-git`
5. **Use `.warp-local` docs for depth:**
   - `PRODUCTION_READINESS_AUDIT.md` for where you are on the 4.5/10 → 10/10 journey.
   - `SPRINT_2WEEKS.md` if you want to execute the 80-hour plan.

---

## 7. Notes on Git & Privacy

- `.warp-local/` and `WARP.md` **should stay in `.gitignore`** so that personal context and analysis do not reach GitHub.
- The backup workflow works at the **git level**; it does not touch `.warp-local/` files.
- Treat `.warp-local/` as **local, personal, and non-versioned** context.

If at any point `.warp-local/` appears in `git status`, either:

```bash
# Re-add ignore rule (if missing)
echo ".warp-local/" >> .gitignore

git restore --staged .warp-local
```

or move the context directory out of the repo before committing.

---

## 8. If You Resume Months Later

Minimal steps to get back up to speed:

```bash
cd /home/bhuvan/Documents/Projects/SecLyzer
source ../venv/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"

bash .warp-local/verify_context.sh
cat .warp-local/CONTEXT_SNAPSHOT.md
cat .warp-local/AGENT_CASCADE_CONTEXT.md
```

After that, pick a task from `.warp-local/SPRINT_2WEEKS.md` or from your own TODOs and continue.
