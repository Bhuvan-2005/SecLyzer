"""
Mouse Feature Extractor
Processes raw mouse events into ML-ready feature vectors
"""

import redis
import json
import polars as pl
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional
import numpy as np
import os

from storage import get_timeseries_db
from common import get_developer_mode
from common.logger import get_logger
from common.retry import retry_with_backoff

logger = get_logger(__name__)

class MouseExtractor:
    def __init__(self, window_seconds: int = 30, update_interval: int = 5):
        """
        Initialize mouse feature extractor
        
        Args:
            window_seconds: Size of sliding window in seconds
            update_interval: How often to calculate features (seconds)
        """
        self.window_seconds = window_seconds
        self.update_interval = update_interval
        
        # Event buffer
        self.events = deque(maxlen=50000)  # Mouse generates more events
        
        # Last update time
        self.last_update = datetime.now()
        
        # Connect to Redis with auth
        redis_password = os.getenv('REDIS_PASSWORD')
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=redis_password if redis_password else None,
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe('seclyzer:events')
        
        # Connect to database
        self.db = get_timeseries_db()
        
        # Developer mode
        self.dev_mode = get_developer_mode()
    
    def process_events(self):
        """Main event processing loop"""
        logger.info("Mouse Extractor starting", component="mouse_extractor")
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    event = json.loads(message['data'])
                    
                    # Only process mouse events
                    if event.get('type') == 'mouse':
                        self._add_event(event)
                        
                        # Check if it's time to calculate features
                        if (datetime.now() - self.last_update).total_seconds() >= self.update_interval:
                            features = self.extract_features()
                            if features:
                                self._save_features(features)
                            self.last_update = datetime.now()
                
                except Exception as e:
                    logger.error("Error processing mouse event", error=str(e), event_type="mouse")
    
    def _add_event(self, event: Dict):
        """Add event to buffer"""
        self.events.append({
            'timestamp': event['ts'] / 1_000_000,  # Convert to seconds
            'x': event.get('x'),
            'y': event.get('y'),
            'event_type': event['event'],
            'button': event.get('button'),
            'scroll_delta': event.get('scroll_delta'),
            'dev_mode': self.dev_mode.is_active() if self.dev_mode else False
        })
    
    def extract_features(self) -> Optional[Dict]:
        """
        Extract features from event buffer
        
        Returns:
            Dict with 38 features, or None if insufficient data
        """
        # Get events from last window
        cutoff_time = datetime.now().timestamp() - self.window_seconds
        recent_events = [e for e in self.events if e['timestamp'] > cutoff_time]
        
        if len(recent_events) < 50:  # Need minimum events
            return None
        
        # Separate movement and click events
        movements = [e for e in recent_events if e['event_type'] == 'move' and e['x'] is not None]
        clicks = [e for e in recent_events if e['event_type'] in ['press', 'release']]
        scrolls = [e for e in recent_events if e['event_type'] == 'scroll']
        
        features = {}
        
        # Movement features
        if len(movements) > 2:
            features.update(self._calculate_movement_features(movements))
        else:
            # Fill with zeros if no data
            features.update({f'move_{i}': 0.0 for i in range(20)})
        
        # Click features
        if clicks:
            features.update(self._calculate_click_features(clicks))
        else:
            features.update({f'click_{i}': 0.0 for i in range(10)})
        
        # Scroll features
        if scrolls:
            features.update(self._calculate_scroll_features(scrolls))
        else:
            features.update({f'scroll_{i}': 0.0 for i in range(8)})
        
        # Add developer mode flag
        features['dev_mode'] = any(e['dev_mode'] for e in recent_events)
        
        return features
    
    def _calculate_movement_features(self, movements: List[Dict]) -> Dict:
        """Calculate movement-based features (velocity, acceleration, curvature)"""
        # Extract coordinates
        x = np.array([m['x'] for m in movements])
        y = np.array([m['y'] for m in movements])
        t = np.array([m['timestamp'] for m in movements])
        
        # Calculate distances traveled
        dx = np.diff(x)
        dy = np.diff(y)
        distances = np.sqrt(dx**2 + dy**2)
        
        # Calculate time deltas
        dt = np.diff(t)
        dt = np.maximum(dt, 0.001)  # Avoid division by zero
        
        # Velocity (pixels/second)
        raw_velocities = distances / dt
        velocities = raw_velocities[raw_velocities < 10000]  # Remove outliers for stats
        
        # Acceleration
        # Calculate from raw velocities to maintain shape alignment with dt
        if len(raw_velocities) > 1:
            dv = np.diff(raw_velocities)
            raw_accelerations = dv / dt[:-1]
            accelerations = raw_accelerations[np.abs(raw_accelerations) < 100000]
        else:
            raw_accelerations = np.array([])
            accelerations = np.array([])
        
        # Direction changes (angles)
        angles = np.arctan2(dy, dx)
        angle_changes = np.abs(np.diff(angles))
        
        # Curvature (straightness of path)
        total_distance = np.sum(distances)
        straight_distance = np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2)
        curvature = 1 - (straight_distance / max(total_distance, 1))
        
        # Jerk (change in acceleration - smoothness indicator)
        if len(raw_accelerations) > 1:
            raw_jerk = np.diff(raw_accelerations) / dt[:-2]
            jerk = raw_jerk[np.abs(raw_jerk) < 1000000]
        else:
            jerk = np.array([0])
        
        return {
            # Velocity features
            'move_0': np.mean(velocities) if len(velocities) > 0 else 0,
            'move_1': np.std(velocities) if len(velocities) > 0 else 0,
            'move_2': np.max(velocities) if len(velocities) > 0 else 0,
            'move_3': np.median(velocities) if len(velocities) > 0 else 0,
            
            # Acceleration features
            'move_4': np.mean(np.abs(accelerations)) if len(accelerations) > 0 else 0,
            'move_5': np.std(accelerations) if len(accelerations) > 0 else 0,
            'move_6': np.max(np.abs(accelerations)) if len(accelerations) > 0 else 0,
            
            # Direction/curvature features
            'move_7': curvature,
            'move_8': np.mean(angle_changes) if len(angle_changes) > 0 else 0,
            'move_9': np.std(angle_changes) if len(angle_changes) > 0 else 0,
            
            # Jerk (smoothness) features
            'move_10': np.mean(np.abs(jerk)) if len(jerk) > 0 else 0,
            'move_11': np.std(jerk) if len(jerk) > 0 else 0,
            
            # Distance features
            'move_12': total_distance,
            'move_13': straight_distance,
            'move_14': total_distance / max(len(movements), 1),  # Avg distance per sample
            
            # Idle time (pauses in movement)
            'move_15': np.sum(dt > 0.1) / max(len(dt), 1),  # Fraction of time idle
            'move_16': np.mean(dt),  # Average time between samples
            'move_17': np.std(dt),
            
            # Movement efficiency
            'move_18': straight_distance / max(total_distance, 1),
            'move_19': len(movements) / self.window_seconds  # Movement frequency
        }
    
    def _calculate_click_features(self, clicks: List[Dict]) -> Dict:
        """Calculate click-based features"""
        # Separate press and release
        presses = [c for c in clicks if c['event_type'] == 'press']
        releases = [c for c in clicks if c['event_type'] == 'release']
        
        # Click durations (time between press and release)
        click_durations = []
        press_times = {c['button']: c['timestamp'] for c in presses}
        
        for release in releases:
            button = release['button']
            if button in press_times:
                duration = (release['timestamp'] - press_times[button]) * 1000  # ms
                if 0 < duration < 5000:  # Sanity check
                    click_durations.append(duration)
                del press_times[button]
        
        # Count clicks by button
        left_clicks = len([c for c in presses if c['button'] == 'Left'])
        right_clicks = len([c for c in presses if c['button'] == 'Right'])
        middle_clicks = len([c for c in presses if c['button'] == 'Middle'])
        
        # Double-click detection (two clicks within 500ms)
        double_clicks = 0
        sorted_presses = sorted(presses, key=lambda x: x['timestamp'])
        for i in range(len(sorted_presses) - 1):
            if (sorted_presses[i+1]['timestamp'] - sorted_presses[i]['timestamp']) < 0.5:
                double_clicks += 1
        
        return {
            'click_0': np.mean(click_durations) if click_durations else 0,
            'click_1': np.std(click_durations) if click_durations else 0,
            'click_2': left_clicks,
            'click_3': right_clicks,
            'click_4': middle_clicks,
            'click_5': left_clicks / max(left_clicks + right_clicks + middle_clicks, 1),  # Left click ratio
            'click_6': double_clicks,
            'click_7': double_clicks / max(len(presses), 1),  # Double click rate
            'click_8': len(presses) / self.window_seconds,  # Click frequency
            'click_9': np.median(click_durations) if click_durations else 0
        }
    
    def _calculate_scroll_features(self, scrolls: List[Dict]) -> Dict:
        """Calculate scroll-based features"""
        # Extract scroll deltas
        deltas = [s['scroll_delta'] for s in scrolls if s['scroll_delta'] is not None]
        
        if not deltas:
            return {f'scroll_{i}': 0.0 for i in range(8)}
        
        # Scroll directions
        up_scrolls = [d for d in deltas if d > 0]
        down_scrolls = [d for d in deltas if d < 0]
        
        # Scroll speeds (time between scrolls)
        times = [s['timestamp'] for s in scrolls]
        scroll_intervals = np.diff(times) if len(times) > 1 else [0]
        
        return {
            'scroll_0': np.mean(np.abs(deltas)),
            'scroll_1': np.std(deltas),
            'scroll_2': len(up_scrolls),
            'scroll_3': len(down_scrolls),
            'scroll_4': len(up_scrolls) / max(len(deltas), 1),  # Up scroll ratio
            'scroll_5': len(scrolls) / self.window_seconds,  # Scroll frequency
            'scroll_6': np.mean(scroll_intervals) if len(scroll_intervals) > 0 else 0,
            'scroll_7': np.std(scroll_intervals) if len(scroll_intervals) > 0 else 0
        }
    
    def _save_features(self, features: Dict):
        """Save features to InfluxDB and publish to Redis"""
        try:
            # 1. Write to InfluxDB (Storage)
            self.db.write_mouse_features(features)
            
            # 2. Publish to Redis (Real-time Inference)
            # Add timestamp and type metadata
            features['timestamp'] = datetime.utcnow().isoformat()
            features['type'] = 'mouse'
            self.redis_client.publish('seclyzer:features:mouse', json.dumps(features))
            
            print(f"[Mouse Extractor] Saved & Published features | Dev mode: {features.get('dev_mode', False)}")
        except Exception as e:
            print(f"[Mouse Extractor] Error saving features: {e}")


if __name__ == '__main__':
    extractor = MouseExtractor()
    extractor.process_events()
