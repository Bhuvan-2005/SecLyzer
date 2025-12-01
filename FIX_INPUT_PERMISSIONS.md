# Input Permissions Fix

## Problem
The collectors cannot capture keyboard/mouse events because the user is not in the `input` group.

## Evidence
```
/dev/input/event* are owned by root:input
User groups: bhuvan adm cdrom sudo dip plugdev users lpadmin (NO input group!)
```

## Solution
1. Add user to input group:
   ```bash
   sudo usermod -aG input $USER
   ```

2. **IMPORTANT**: Log out and log back in for group change to take effect

3. Verify:
   ```bash
   groups  # Should show "input"
   ```

4. Restart services:
   ```bash
   ./scripts/dev restart
   ```

5. Test:
   ```bash
   # Type something, then:
   tail -f /var/log/seclyzer/keystroke_extractor.log
   # Should see "Saved" messages every second
   ```

## Why This Happened
The Rust collectors need direct access to `/dev/input/event*` devices to capture raw input events. Without `input` group membership, they silently fail to read events (permission denied).
