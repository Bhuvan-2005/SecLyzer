#!/usr/bin/env python3
"""
Developer Mode Module
Provides authentication bypass for development/debugging

⚠ WARNING: This is a SECURITY BYPASS!
Only use in development environments.
"""

import os
import hashlib
import time
import yaml
from pathlib import Path
from datetime import datetime, timedelta

class DeveloperMode:
    def __init__(self, config_path="/etc/seclyzer/dev_mode.yml"):
        """Initialize developer mode handler"""
        self.config_path = config_path
        self.config = self._load_config()
        self.active = False
        self.activation_time = None
        self.activation_method = None
        
    def _load_config(self):
        """Load developer mode configuration"""
        if not os.path.exists(self.config_path):
            # Developer mode disabled if config doesn't exist
            return {"enabled": False}
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def is_active(self):
        """Check if developer mode is currently active"""
        if not self.config.get('enabled', False):
            return False
        
        # Check auto-disable timeout
        if self.active and self.activation_time:
            auto_disable_hours = self.config.get('security', {}).get('auto_disable_hours', 0)
            if auto_disable_hours > 0:
                timeout = self.activation_time + timedelta(hours=auto_disable_hours)
                if datetime.now() > timeout:
                    self._deactivate("Auto-disabled after timeout")
                    return False
        
        # Method 1: Check for magic file
        if self._check_magic_file():
            if not self.active:
                self._activate("Magic file detected")
            return True
        
        # Method 2: Check environment variable
        if self._check_env_var():
            if not self.active:
                self._activate("Environment variable set")
            return True
        
        # If previously activated by key sequence, check if still valid
        if self.active and self.activation_method == "key_sequence":
            duration = self.config.get('key_sequence', {}).get('duration_minutes', 5)
            timeout = self.activation_time + timedelta(minutes=duration)
            if datetime.now() > timeout:
                self._deactivate("Key sequence timeout expired")
                return False
            return True
        
        return self.active
    
    def _check_magic_file(self):
        """Check if magic file exists"""
        if not self.config.get('magic_file', {}).get('enabled', False):
            return False
        
        magic_path = self.config['magic_file']['path']
        return os.path.exists(magic_path)
    
    def _check_env_var(self):
        """Check if environment variable is set"""
        if not self.config.get('env_var', {}).get('enabled', False):
            return False
        
        var_name = self.config['env_var']['name']
        return os.environ.get(var_name) == "1"
    
    def check_key_sequence(self, recent_keys):
        """
        Check if recent key presses match the developer sequence
        
        Args:
            recent_keys: List of recent key names (e.g., ["LeftCtrl", "LeftShift", "F12"])
        
        Returns:
            bool: True if sequence matched and dev mode activated
        """
        if not self.config.get('key_sequence', {}).get('enabled', False):
            return False
        
        expected_sequence = self.config['key_sequence']['sequence']
        
        # Check if recent keys match the sequence
        if len(recent_keys) >= len(expected_sequence):
            actual = recent_keys[-len(expected_sequence):]
            if actual == expected_sequence:
                self._activate("Key sequence detected")
                return True
        
        return False
    
    def check_password(self, typed_text):
        """
        Check if typed text contains the developer password
        
        Args:
            typed_text: Recent typed text to check
        
        Returns:
            bool: True if password matched
        """
        if not self.config.get('password_override', {}).get('enabled', False):
            return False
        
        # Hash the typed text and compare
        text_hash = hashlib.sha256(typed_text.encode()).hexdigest()
        expected_hash = self.config['password_override']['password_hash']
        
        if text_hash == expected_hash:
            self._activate("Password override")
            return True
        
        return False
    
    def _activate(self, method):
        """Activate developer mode"""
        self.active = True
        self.activation_time = datetime.now()
        self.activation_method = method
        
        # Log activation
        if self.config.get('security', {}).get('audit_log', True):
            self._log_event("ACTIVATED", method)
        
        # Show warning (if configured)
        if self.config.get('security', {}).get('show_warning', True):
            self._show_warning()
    
    def _deactivate(self, reason):
        """Deactivate developer mode"""
        if self.active:
            self._log_event("DEACTIVATED", reason)
        
        self.active = False
        self.activation_time = None
        self.activation_method = None
    
    def _log_event(self, event_type, details):
        """Log developer mode events"""
        audit_file = self.config.get('security', {}).get('audit_file', '/var/log/seclyzer/dev_mode.log')
        
        # Create log directory if needed
        os.makedirs(os.path.dirname(audit_file), exist_ok=True)
        
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} | {event_type} | {details}\n"
        
        try:
            with open(audit_file, 'a') as f:
                f.write(log_entry)
        except PermissionError:
            # Fallback to user's home directory
            fallback = os.path.expanduser("~/.seclyzer_dev_mode.log")
            with open(fallback, 'a') as f:
                f.write(log_entry)
    
    def _show_warning(self):
        """Show visual warning that dev mode is active"""
        message = self.config.get('security', {}).get('warning_message', 
                                                       '⚠ DEVELOPER MODE ACTIVE')
        
        # Try to show desktop notification
        try:
            import subprocess
            subprocess.run(['notify-send', 
                          'SecLyzer Developer Mode',
                          message,
                          '--urgency=critical',
                          '--icon=dialog-warning'],
                         check=False)
        except:
            # Fallback to console
            print(f"\n{'='*60}")
            print(f"  {message}")
            print(f"{'='*60}\n")
    
    def get_bypass_score(self):
        """
        Return what score to use when dev mode is active
        
        Returns:
            float: Confidence score (0-100)
        """
        # Always return 100% when in dev mode (full trust)
        return 100.0
    
    def should_bypass_lockdown(self):
        """
        Check if lockdown should be bypassed
        
        Returns:
            bool: True if dev mode active and should bypass
        """
        return self.is_active()
    
    def get_metadata_tag(self):
        """
        Get metadata to tag collected data
        
        Returns:
            dict: Metadata to attach to events/features
        """
        if self.is_active():
            return {
                'dev_mode': True,
                'dev_mode_method': self.activation_method,
                'dev_mode_activated_at': self.activation_time.isoformat() if self.activation_time else None
            }
        return {
            'dev_mode': False
        }
    
    def should_include_in_training(self):
        """
        Check if data from current session should be used for training
        
        Returns:
            bool: False if dev mode active (exclude from training)
        """
        return not self.is_active()


# Convenience functions for integration

_dev_mode_instance = None

def init_developer_mode(config_path=None):
    """Initialize developer mode (call once at startup)"""
    global _dev_mode_instance
    if config_path is None:
        # Try multiple locations
        for path in ["/etc/seclyzer/dev_mode.yml",
                     "/home/bhuvan/Documents/Projects/SecLyzer/config/dev_mode.yml"]:
            if os.path.exists(path):
                config_path = path
                break
    
    _dev_mode_instance = DeveloperMode(config_path)
    return _dev_mode_instance

def is_developer_mode_active():
    """Quick check if developer mode is active"""
    if _dev_mode_instance is None:
        init_developer_mode()
    return _dev_mode_instance.is_active()

def get_developer_mode():
    """Get developer mode instance"""
    if _dev_mode_instance is None:
        init_developer_mode()
    return _dev_mode_instance


# Example usage in decision engine:
"""
from common.developer_mode import is_developer_mode_active, get_developer_mode

def make_authentication_decision(confidence_score):
    # Check developer mode first
    if is_developer_mode_active():
        dev_mode = get_developer_mode()
        return {
            'allow': True,
            'score': dev_mode.get_bypass_score(),
            'reason': 'Developer mode active (BYPASS)'
        }
    
    # Normal authentication logic
    if confidence_score >= 90:
        return {'allow': True, 'score': confidence_score}
    elif confidence_score < 50:
        return {'allow': False, 'score': confidence_score, 'action': 'lockdown'}
    # ... etc
"""
