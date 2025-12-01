# SecLyzer Developer Mode Guide

## ⚠ SECURITY WARNING ⚠

**Developer mode COMPLETELY DISABLES all authentication checks!**

- Only use in development/testing environments
- Never enable in production
- Remove `config/dev_mode.yml` before deploying

---

## What is Developer Mode?

When you're developing or debugging SecLyzer, you might:
- Trigger false positives (get locked out constantly)
- Need to test with unusual typing patterns
- Want to bypass authentication to focus on other features

Developer mode provides a **secret backdoor** that only you know about.

---

## Activation Methods

You have **4 ways** to activate developer mode (any one works):

### Method 1: Magic File (Simplest)

Create a special file to activate dev mode:

```bash
touch /tmp/.seclyzer_dev_mode
```

**To deactivate:**
```bash
rm /tmp/.seclyzer_dev_mode
```

**Best for:** Long debugging sessions

---

### Method 2: Key Sequence (Cool!)

Press a secret key combination:

**Default sequence:** `Ctrl + Shift + F12` (press F12 three times rapidly)

**Effect:** Disables auth for 5 minutes

**Best for:** Quick testing without leaving terminal

---

### Method 3: Environment Variable

Set an environment variable before running:

```bash
export SECLYZER_DEV_MODE=1
./collectors/keyboard_collector  # Runs with dev mode active
```

**Best for:** Testing in isolated processes

---

### Method 4: Password Override (Most Secure)

Type a secret password anywhere (in any text field) to activate.

**Default password:** `SecLyzerDevMode2024` (CHANGE THIS!)

**How to change:**
```bash
# Generate hash of your secret password
echo -n "YourSecretPassword123" | sha256sum

# Copy the hash and update config/dev_mode.yml:
# password_hash: "<your_hash_here>"
```

**Best for:** Sharing dev mode with team members without sharing files

---

## Configuration

Edit [`config/dev_mode.yml`](file:///home/bhuvan/Documents/Projects/SecLyzer/config/dev_mode.yml) to customize:

```yaml
# Enable/disable developer mode entirely
enabled: true

# Enable/disable specific methods
magic_file:
  enabled: true
  path: "/tmp/.seclyzer_dev_mode"

key_sequence:
  enabled: true
  sequence: ["LeftCtrl", "LeftShift", "F12", "F12", "F12"]
  duration_minutes: 5  # How long it stays active

env_var:
  enabled: true
  name: "SECLYZER_DEV_MODE"

password_override:
  enabled: true
  password_hash: "<your_custom_hash>"

security:
  audit_log: true  # Log all activations
  show_warning: true  # Show desktop notification
  auto_disable_hours: 24  # Auto-disable after 1 day
```

---

## How It Works Internally

When developer mode is active:

1. **Authentication is bypassed:** Confidence score is always 100%
2. **No lockdowns:** Decision engine always allows access
3. **Audit logging:** All activations are logged (see below)
4. **Visual warning:** Desktop notification shows dev mode is active

---

## Security Features

### Audit Logging

All developer mode activations are logged:

```
/var/log/seclyzer/dev_mode.log
```

Example log entry:
```
2024-11-27T17:15:30 | ACTIVATED | Magic file detected
2024-11-27T17:45:30 | DEACTIVATED | Auto-disabled after timeout
```

### Visual Warning

When activated, you'll see:

```
╔═══════════════════════════════════════╗
║ ⚠ DEVELOPER MODE ACTIVE - AUTH DISABLED ⚠ ║
╚═══════════════════════════════════════╝
```

Plus a desktop notification (if libnotify available).

### Auto-Disable

By default, dev mode auto-disables after 24 hours (configurable).

---

## Usage Examples

### Scenario 1: Debugging Keyboard Collector

```bash
# Activate dev mode
touch /tmp/.seclyzer_dev_mode

# Run collector - won't trigger lockouts
sudo collectors/keyboard_collector/target/release/keyboard_collector

# Type weird things, change typing speed, etc.
# No auth failures!

# When done
rm /tmp/.seclyzer_dev_mode
```

### Scenario 2: Testing Different User Profiles

```bash
# Set env var
export SECLYZER_DEV_MODE=1

# Run SecLyzer
python daemon/seclyzer_daemon.py

# Simulate different users typing
# System won't lock you out

# Unset when done
unset SECLYZER_DEV_MODE
```

### Scenario 3: Emergency Bypass (Already Locked Out)

If you're already locked out:

1. Switch to TTY (Ctrl+Alt+F3)
2. Login
3. Create magic file:
   ```bash
   touch /tmp/.seclyzer_dev_mode
   ```
4. Switch back to GUI (Ctrl+Alt+F2)
5. Screen should unlock automatically

---

## Production Deployment

**Before deploying SecLyzer in production:**

1. **Delete the dev mode config:**
   ```bash
   sudo rm /etc/seclyzer/dev_mode.yml
   ```

2. **Verify it's disabled:**
   ```bash
   # Try to activate - should fail
   touch /tmp/.seclyzer_dev_mode
   # Check logs - should show "Developer mode disabled"
   ```

3. **Remove from git:**
   ```bash
   git rm config/dev_mode.yml
   git commit -m "Remove developer mode for production"
   ```

---

## Integration with SecLyzer

Developer mode integrates at the **Decision Engine** level:

```python
# In processing/decision/decision_engine.py
from common.developer_mode import is_developer_mode_active, get_developer_mode

def make_decision(confidence_score):
    # Check developer mode FIRST
    if is_developer_mode_active():
        dev = get_developer_mode()
        return {
            'allow': True,
            'score': dev.get_bypass_score(),  # Always 100
            'reason': 'Developer mode active (BYPASS)',
            'action': 'allow'
        }
    
    # Normal authentication logic
    if confidence_score >= 90:
        return {'allow': True, ...}
    # ... rest of logic
```

This means:
- ✅ All ML models still run (you can see their scores)
- ✅ Data is still collected (training continues)
- ✅ Only the final decision is overridden

---

## Troubleshooting

### "Developer mode not activating"

1. Check if config exists:
   ```bash
   ls -l /etc/seclyzer/dev_mode.yml
   ```

2. Check if enabled in config:
   ```bash
   grep "enabled: true" /etc/seclyzer/dev_mode.yml
   ```

3. Check logs:
   ```bash
   tail -f /var/log/seclyzer/dev_mode.log
   ```

### "Magic file not working"

Make sure the path matches:
```bash
# Check config
grep "path:" /etc/seclyzer/dev_mode.yml

# Create file at that exact path
touch /tmp/.seclyzer_dev_mode
```

### "Key sequence not detected"

- Make sure you press keys within 3 seconds
- Press F12 exactly 3 times
- Hold Ctrl+Shift throughout

---

## Advanced: Custom Shortcuts

You can add custom developer shortcuts in `config/dev_mode.yml`:

```yaml
shortcuts:
  # Force confidence score to 100%
  force_score_shortcut:
    enabled: true
    key: "F9"
    modifier: "LeftCtrl"  # Ctrl+F9
  
  # Show real-time debug overlay
  debug_overlay_shortcut:
    enabled: true
    key: "F10"
    modifier: "LeftCtrl"  # Ctrl+F10
```

These will be implemented in Phase 2+ as we build the decision engine.

---

## Summary

**Developer mode is YOUR secret debugging tool.**

- 🔓 Bypasses all authentication
- 🔍 Fully audited (every activation logged)
- ⚠️ Clearly visible when active
- 🛡️ Disabled by default in production
- 🔑 Only YOU know the activation methods

**Change the default password hash immediately!**

```bash
echo -n "YourSuperSecretPassword" | sha256sum
# Update config/dev_mode.yml with the hash
```

This backdoor is **only for you**, on **your machine**, for **development**. Keep it secret!
