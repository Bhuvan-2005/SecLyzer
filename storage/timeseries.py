"""
InfluxDB Time-Series Database Wrapper
Handles behavioral feature storage and retrieval
"""

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import os
from common.retry import retry_with_backoff
from common.logger import get_logger

logger = get_logger(__name__)

class TimeSeriesDB:
    def __init__(self, url: str = "http://localhost:8086",
                 token: str = None,
                 org: str = "seclyzer",
                 bucket: str = "behavioral_data"):
        """Initialize InfluxDB connection"""
        
        # Try to read token from file if not provided
        if token is None:
            token_file = "/etc/seclyzer/influxdb_token"
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    token = f.read().strip()
        
        # Get config from environment or defaults, overriding provided args if env vars exist
        # This allows environment variables to take precedence for deployment flexibility
        self.url = os.getenv('INFLUX_URL', url)
        self.token = os.getenv('INFLUX_TOKEN', token if token is not None else '') # Use provided token if not None, else empty string for env fallback
        self.org = os.getenv('INFLUX_ORG', org)
        self.bucket = os.getenv('INFLUX_BUCKET', bucket)
        
        # Initialize client
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
    
    def close(self):
        """Close connection"""
        self.client.close()
    
    # ===== Write Functions =====
    
    @retry_with_backoff(max_attempts=3, initial_delay=0.5)
    def write_keystroke_features(self, features: Dict, user_id: str = "default",
                                 device_id: str = "keyboard_0",
                                 timestamp: Optional[datetime] = None):
        """Write keystroke features to database"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        point = Point("keystroke_features") \
            .tag("user_id", user_id) \
            .tag("device_id", device_id)
        
        # Add all features as fields
        for key, value in features.items():
            if isinstance(value, (int, float)):
                point = point.field(key, float(value))
        
        point = point.time(timestamp, WritePrecision.NS)
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
    
    def write_mouse_features(self, features: Dict, user_id: str = "default",
                            timestamp: Optional[datetime] = None):
        """Write mouse features to database"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        point = Point("mouse_features") \
            .tag("user_id", user_id)
        
        for key, value in features.items():
            if isinstance(value, (int, float)):
                point = point.field(key, float(value))
        
        point = point.time(timestamp, WritePrecision.NS)
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
    
    def write_app_transition(self, from_app: str, to_app: str,
                            duration_ms: int, user_id: str = "default",
                            timestamp: Optional[datetime] = None):
        """Write application transition"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        point = Point("app_transitions") \
            .tag("user_id", user_id) \
            .tag("from_app", from_app) \
            .tag("to_app", to_app) \
            .field("duration_ms", float(duration_ms)) \
            .time(timestamp, WritePrecision.NS)
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
    
    def write_confidence_score(self, keystroke_score: float, mouse_score: float,
                               fused_score: float, state: str,
                               user_id: str = "default",
                               timestamp: Optional[datetime] = None):
        """Write confidence scores"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        point = Point("confidence_scores") \
            .tag("user_id", user_id) \
            .tag("state", state) \
            .field("keystroke_score", float(keystroke_score)) \
            .field("mouse_score", float(mouse_score)) \
            .field("fused_score", float(fused_score)) \
            .time(timestamp, WritePrecision.NS)
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
    
    # ===== Query Functions =====
    
    def query_keystroke_features(self, start_time: datetime, end_time: datetime,
                                 user_id: str = "default") -> List[Dict]:
        """Query keystroke features in time range"""
        query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r["_measurement"] == "keystroke_features")
            |> filter(fn: (r) => r["user_id"] == "{user_id}")
        '''
        
        result = self.query_api.query(org=self.org, query=query)
        return self._parse_query_result(result)
    
    def query_mouse_features(self, start_time: datetime, end_time: datetime,
                            user_id: str = "default") -> List[Dict]:
        """Query mouse features in time range"""
        query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r["_measurement"] == "mouse_features")
            |> filter(fn: (r) => r["user_id"] == "{user_id}")
        '''
        
        result = self.query_api.query(org=self.org, query=query)
        return self._parse_query_result(result)
    
    def query_recent_features(self, measurement: str, minutes: int = 1,
                             user_id: str = "default") -> List[Dict]:
        """Query features from last N minutes"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=minutes)
        
        query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: {start_time.isoformat()}Z)
            |> filter(fn: (r) => r["_measurement"] == "{measurement}")
            |> filter(fn: (r) => r["user_id"] == "{user_id}")
        '''
        
        result = self.query_api.query(org=self.org, query=query)
        return self._parse_query_result(result)
    
    def get_latest_score(self, user_id: str = "default") -> Optional[Dict]:
        """Get most recent confidence score"""
        query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "confidence_scores")
            |> filter(fn: (r) => r["user_id"] == "{user_id}")
            |> last()
        '''
        
        result = self.query_api.query(org=self.org, query=query)
        results = self._parse_query_result(result)
        return results[0] if results else None
    
    # ===== Utility Functions =====
    
    def _parse_query_result(self, result) -> List[Dict]:
        """Parse Flux query result into list of dicts"""
        records = []
        for table in result:
            for record in table.records:
                records.append({
                    'time': record.get_time(),
                    'field': record.get_field(),
                    'value': record.get_value(),
                    **record.values
                })
        return records
    
    def delete_old_data(self, older_than_days: int = 30):
        """Delete data older than specified days"""
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        stop = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        
        delete_api = self.client.delete_api()
        delete_api.delete(
            start=start,
            stop=stop,
            predicate='_measurement="keystroke_features" OR _measurement="mouse_features"',
            bucket=self.bucket,
            org=self.org
        )
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()


# Convenience function
def get_timeseries_db(config_path: str = "/etc/seclyzer/seclyzer.yml") -> TimeSeriesDB:
    """Get InfluxDB instance from config"""
    import yaml
    
    # Try to load from config
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        influx_config = config.get('database', {}).get('influxdb', {})
        return TimeSeriesDB(
            url=influx_config.get('url', 'http://localhost:8086'),
            token=influx_config.get('token'),
            org=influx_config.get('org', 'seclyzer'),
            bucket=influx_config.get('bucket', 'behavioral_data')
        )
    
    # Fallback to defaults
    return TimeSeriesDB()
