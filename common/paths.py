"""
XDG Base Directory support for SecLyzer
Provides cross-platform path resolution following XDG specification
"""
import os
from pathlib import Path
from typing import Optional


def get_data_dir(app_name: str = "seclyzer") -> Path:
    """
    Get data directory following XDG Base Directory spec
    
    Priority:
    1. XDG_DATA_HOME/seclyzer
    2. ~/.local/share/seclyzer
    3. /var/lib/seclyzer (system-wide)
    
    Returns:
        Path to data directory
    """
    # Check if running as root or with sudo
    is_system_install = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
    
    if is_system_install:
        return Path("/var/lib") / app_name
    
    # User-mode installation
    xdg_data_home = os.getenv('XDG_DATA_HOME')
    if xdg_data_home:
        return Path(xdg_data_home) / app_name
    
    return Path.home() / ".local" / "share" / app_name


def get_config_dir(app_name: str = "seclyzer") -> Path:
    """
    Get config directory following XDG Base Directory spec
    
    Priority:
    1. XDG_CONFIG_HOME/seclyzer
    2. ~/.config/seclyzer
    3. /etc/seclyzer (system-wide)
    
    Returns:
        Path to config directory
    """
    is_system_install = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
    
    if is_system_install:
        return Path("/etc") / app_name
    
    xdg_config_home = os.getenv('XDG_CONFIG_HOME')
    if xdg_config_home:
        return Path(xdg_config_home) / app_name
    
    return Path.home() / ".config" / app_name


def get_cache_dir(app_name: str = "seclyzer") -> Path:
    """
    Get cache directory following XDG Base Directory spec
    
    Priority:
    1. XDG_CACHE_HOME/seclyzer
    2. ~/.cache/seclyzer
    3. /var/cache/seclyzer (system-wide)
    
    Returns:
        Path to cache directory
    """
    is_system_install = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
    
    if is_system_install:
        return Path("/var/cache") / app_name
    
    xdg_cache_home = os.getenv('XDG_CACHE_HOME')
    if xdg_cache_home:
        return Path(xdg_cache_home) / app_name
    
    return Path.home() / ".cache" / app_name


def get_log_dir(app_name: str = "seclyzer") -> Path:
    """
    Get log directory
    
    For system installs: /var/log/seclyzer
    For user installs: ~/.cache/seclyzer/logs
    
    Returns:
        Path to log directory
    """
    is_system_install = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
    
    if is_system_install:
        return Path("/var/log") / app_name
    
    return get_cache_dir(app_name) / "logs"


def ensure_directories() -> dict:
    """
    Create all required directories if they don't exist
    
    Returns:
        Dictionary with paths
    """
    paths = {
        'data': get_data_dir(),
        'config': get_config_dir(),
        'cache': get_cache_dir(),
        'logs': get_log_dir(),
    }
    
    for name, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (paths['data'] / 'databases').mkdir(exist_ok=True)
    (paths['data'] / 'models').mkdir(exist_ok=True)
    (paths['data'] / 'backups').mkdir(exist_ok=True)
    
    return paths


def get_database_path(db_name: str = "seclyzer.db") -> Path:
    """Get path to SQLite database"""
    return get_data_dir() / "databases" / db_name


def get_models_dir() -> Path:
    """Get path to models directory"""
    return get_data_dir() / "models"


def get_backups_dir() -> Path:
    """Get path to backups directory"""
    return get_data_dir() / "backups"


# Initialize paths on module import
_paths = ensure_directories()
