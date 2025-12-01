"""
Configuration management for SecLyzer
Loads config from YAML and environment variables
"""
import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
from common.logger import get_logger

logger = get_logger(__name__)


class Config:
    """Centralized configuration manager"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load()
    
    def load(self, config_path: Optional[str] = None):
        """Load configuration from file"""
        if config_path is None:
            # Try multiple locations
            locations = [
                os.getenv('SECLYZER_CONFIG'),
                os.path.join(os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), 'seclyzer', 'config.yaml'),
                '/etc/seclyzer/config.yaml',
                os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml.example')
            ]
            
            for loc in locations:
                if loc and os.path.exists(loc):
                    config_path = loc
                    break
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Loaded config from {config_path}")
        else:
            logger.warning("No config file found, using defaults")
            self._config = self._get_defaults()
    
    def _get_defaults(self) -> Dict:
        """Get default configuration"""
        return {
            'user': {'id': 'primary'},
            'databases': {
                'influxdb': {
                    'url': 'http://localhost:8086',
                    'org': 'seclyzer',
                    'bucket': 'seclyzer'
                },
                'sqlite': {
                    'path': '/var/lib/seclyzer/databases/seclyzer.db'
                },
                'redis': {
                    'host': 'localhost',
                    'port': 6379
                }
            },
            'extractors': {
                'keystroke': {'window_seconds': 30, 'update_interval': 5, 'enabled': True},
                'mouse': {'window_seconds': 30, 'update_interval': 5, 'enabled': True},
                'app': {'update_interval': 60, 'enabled': True}
            },
            'models': {
                'keystroke': {'threshold': 0.5, 'weight': 0.5},
                'mouse': {'threshold': 0.5, 'weight': 0.3},
                'app': {'threshold': 0.3, 'weight': 0.2}
            },
            'trust_scorer': {
                'window_size': 10,
                'warning_threshold': 0.4,
                'alert_threshold': 0.3
            },
            'logging': {
                'level': 'INFO',
                'format': 'json'
            },
            'paths': {
                'data_dir': '/var/lib/seclyzer',
                'config_dir': '/etc/seclyzer',
                'log_dir': '/var/log/seclyzer'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot notation (e.g. 'databases.redis.host')"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_user_id(self) -> str:
        """Get configured user ID"""
        return self.get('user.id', 'primary')
    
    def get_redis_config(self) -> Dict:
        """Get Redis configuration"""
        return {
            'host': os.getenv('REDIS_HOST', self.get('databases.redis.host', 'localhost')),
            'port': int(os.getenv('REDIS_PORT', self.get('databases.redis.port', 6379))),
            'password': os.getenv('REDIS_PASSWORD')
        }
    
    def get_influx_config(self) -> Dict:
        """Get InfluxDB configuration"""
        return {
            'url': os.getenv('INFLUX_URL', self.get('databases.influxdb.url', 'http://localhost:8086')),
            'token': os.getenv('INFLUX_TOKEN', ''),
            'org': os.getenv('INFLUX_ORG', self.get('databases.influxdb.org', 'seclyzer')),
            'bucket': os.getenv('INFLUX_BUCKET', self.get('databases.influxdb.bucket', 'seclyzer'))
        }


# Global config instance
_config = Config()

def get_config() -> Config:
    """Get the global config instance"""
    return _config
