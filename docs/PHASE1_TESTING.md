# Phase 1 Testing Guide - Data Collectors

## Prerequisites
Before testing, ensure:
1. Rust is installed (`rustc --version`)
2. Redis is installed and configured

## Step 1: Setup Redis

```bash
cd ~/SecLyzer
./scripts/setup_redis.sh
```

This will:
- Install Redis if not present
- Configure memory limits (256 MB)
- Bind to localhost only (security)
- Start Redis service

**Verify Redis is running:**
```bash
redis-cli ping
# Should output: PONG
```

## Step 2: Build Collectors

Build all three Rust collectors:

```bash
cd collectors/keyboard_collector
cargo build --release

cd ../mouse_collector
cargo build --release

cd ../app_monitor
cargo build --release
```

**Expected output:** All three should compile successfully.

**Binaries will be at:**
- `collectors/keyboard_collector/target/release/keyboard_collector`
- `collectors/mouse_collector/target/release/mouse_collector`
- `collectors/app_monitor/target/release/app_monitor`

## Step 3: Test Event Monitor

First, ensure the Python Redis library is installed:

```bash
source ~/.seclyzer-venv/bin/activate
pip install redis
```

Run the event monitor in one terminal:

```bash
python3 scripts/event_monitor.py
```

You should see:
```
==============================================================
SecLyzer Event Monitor
==============================================================
Connecting to Redis...
✓ Connected to Redis

Listening for events on 'seclyzer:events' channel...
Press Ctrl+C to stop
--------------------------------------------------------------
```

Leave this running - it will show events as they arrive.

## Step 4: Test Keyboard Collector

Open a NEW terminal and run:

```bash
cd ~/SecLyzer
sudo collectors/keyboard_collector/target/release/keyboard_collector
```

**Why sudo?** Keyboard collector needs root to access raw input devices.

**Expected output:**
```
[Keyboard Collector] Starting...
[Keyboard Collector] Connected to Redis
[Keyboard Collector] Listening for keyboard events (Ctrl+C to stop)
```

**Now type something.** You should see events in the event monitor terminal:
```
[16:52:45.123] KEYSTROKE: KeyH (press)
[16:52:45.223] KEYSTROKE: KeyH (release)
[16:52:45.345] KEYSTROKE: KeyE (press)
[16:52:45.445] KEYSTROKE: KeyE (release)
```

✅ **Success criteria**: Every key press/release appears in monitor

## Step 5: Test Mouse Collector

Open ANOTHER terminal:

```bash
cd ~/SecLyzer
sudo collectors/mouse_collector/target/release/mouse_collector
```

**Expected output:**
```
[Mouse Collector] Starting...
[Mouse Collector] Connected to Redis
[Mouse Collector] Listening for mouse events (Ctrl+C to stop)
```

**Move your mouse and click.** You should see in event monitor:
```
[16:53:01.100] MOUSE MOVE: x=500, y=300
[16:53:01.110] MOUSE MOVE: x=502, y=301
[16:53:02.050] MOUSE PRESS: Left
[16:53:02.150] MOUSE RELEASE: Left
```

✅ **Success criteria**: Mouse movements and clicks appear

## Step 6: Test App Monitor

Open ANOTHER terminal:

```bash
cd ~/SecLyzer
collectors/app_monitor/target/release/app_monitor
```

**Note:** App monitor does NOT need sudo (only reads window info)

**Expected output:**
```
[App Monitor] Starting...
[App Monitor] Connected to Redis
[App Monitor] Connected to X11
[App Monitor] Monitoring active window (Ctrl+C to stop)
```

**Switch between applications** (e.g., terminal → browser → back to terminal)

You should see in event monitor:
```
[16:54:10.000] APP SWITCH: firefox (Navigator)
[16:54:15.000] APP SWITCH: gnome-terminal-server (Gnome-terminal)
```

✅ **Success criteria**: App switches are detected

## Step 7: Verify in Redis Directly

You can also check Redis directly:

```bash
redis-cli
> SUBSCRIBE seclyzer:events
```

You should see raw JSON events:
```json
{"type":"keystroke","ts":1234567890123456,"key":"KeyA","event":"press"}
```

Press Ctrl+C to exit.

## Step 8: Check Redis Memory Usage

```bash
redis-cli INFO memory | grep used_memory_human
```

Should show something like:
```
used_memory_human:5.23M
```

This should stay well under 256 MB limit.

## Troubleshooting

### "Failed to connect to Redis"
```bash
sudo systemctl status redis-server
sudo systemctl start redis-server
```

### Keyboard/Mouse collector: "Permission denied"
Make sure you're running with `sudo`:
```bash
sudo collectors/.../keyboard_collector
```

### App Monitor: "Failed to connect to X11"
Make sure you're on X11, not Wayland:
```bash
echo $XDG_SESSION_TYPE
# Should output: x11
```

If Wayland, log out and switch to X11 session at login screen.

### No events appearing in monitor
1. Check Redis is running: `redis-cli ping`
2. Verify collectors show "Connected to Redis"
3. Make sure event_monitor.py is subscribed to correct channel

## Success Checklist

- [ ] Redis installed and running
- [ ] All three collectors compile successfully
- [ ] Keyboard events captured (press/release)
- [ ] Mouse events captured (move, click, scroll)
- [ ] App switch events captured
- [ ] Events visible in event_monitor.py
- [ ] Redis memory usage < 50 MB

## Next Steps

Once all tests pass:
1. Stop all collectors (Ctrl+C in each terminal)
2. Verify no errors occurred
3. Report back for Phase 2 (Feature Extraction)
