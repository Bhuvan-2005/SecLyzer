"""
Application Usage Tracker
Monitors app switching patterns and builds behavioral profile
"""

import redis
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from typing import Dict, List, Optional
import numpy as np
import os

from storage import get_timeseries_db, get_database
from common import get_developer_mode
from common.logger import get_logger
from common.retry import retry_with_backoff

logger = get_logger(__name__)

class AppTracker:
    def __init__(self, update_interval: int = 60):
        """
        Initialize app usage tracker
        
        Args:
            update_interval: How often to update patterns (seconds)
        """
        self.update_interval = update_interval
        
        # Track app transitions
        self.transitions = defaultdict(int)  # (from_app, to_app) -> count
        self.app_durations = defaultdict(list)  # app -> list of durations (seconds)
        self.time_patterns = defaultdict(lambda: defaultdict(int))  # app -> {hour -> count}
        
        # Current app tracking
        self.current_app = None
        self.current_app_start = None
        
        # Recent events
        self.recent_events = deque(maxlen=1000)
        
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
        
        # Connect to databases
        self.ts_db = get_timeseries_db()
        self.db = get_database()
        
        # Developer mode
        self.dev_mode = get_developer_mode()
    
    def process_events(self):
        """Main event processing loop"""
        logger.info("App Tracker starting", component="app_tracker")
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    event = json.loads(message['data'])
                    
                    # Only process app events
                    if event.get('type') == 'app':
                        self._handle_app_switch(event)
                        
                        # Check if it's time to update patterns
                        if (datetime.now() - self.last_update).total_seconds() >= self.update_interval:
                            self._update_patterns()
                            self.last_update = datetime.now()
                
                except Exception as e:
                    logger.error("Error processing app event", error=str(e), event_type="app")
    
    def _handle_app_switch(self, event: Dict):
        """Handle application switch event"""
        new_app = event['app_name']
        timestamp = event['ts'] / 1_000_000  # Convert to seconds
        current_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        # Record transition
        if self.current_app is not None and self.current_app != new_app:
            # Calculate duration in current app
            duration = timestamp - self.current_app_start.timestamp()
            self.app_durations[self.current_app].append(duration)
            
            # Record transition
            transition = (self.current_app, new_app)
            self.transitions[transition] += 1
            
            # Save to time-series database
            try:
                # 1. Write to InfluxDB (Storage)
                self.ts_db.write_app_transition(
                    from_app=self.current_app,
                    to_app=new_app,
                    duration_ms=int(duration * 1000),
                    timestamp=current_time
                )
                
                # 2. Publish to Redis (Real-time Inference)
                feature_data = {
                    'from_app': self.current_app,
                    'to_app': new_app,
                    'duration_ms': int(duration * 1000),
                    'timestamp': current_time.isoformat(),
                    'type': 'app'
                }
                self.redis_client.publish('seclyzer:features:app', json.dumps(feature_data))
                
            except Exception as e:
                print(f"[App Tracker] Error saving transition: {e}")
                import traceback
                traceback.print_exc()
        
        # Update current app
        self.current_app = new_app
        self.current_app_start = current_time
        
        # Record time pattern (hour of day)
        hour = current_time.hour
        self.time_patterns[new_app][hour] += 1
        
        # Add to recent events
        self.recent_events.append({
            'app': new_app,
            'timestamp': timestamp,
            'hour': hour,
            'dev_mode': self.dev_mode.is_active() if self.dev_mode else False
        })
        
        print(f"[App Tracker] Switched to: {new_app}")
    
    def _update_patterns(self):
        """Update and save usage patterns"""
        # Calculate transition probabilities
        transition_probs = self._calculate_transition_matrix()
        
        # Calculate time-of-day preferences
        time_prefs = self._calculate_time_preferences()
        
        # Calculate usage statistics
        usage_stats = self._calculate_usage_stats()
        
        # Save to database
        patterns = {
            'transition_matrix': transition_probs,
            'time_preferences': time_prefs,
            'usage_stats': usage_stats,
            'dev_mode': any(e['dev_mode'] for e in self.recent_events)
        }
        
        self.db.set_config('app_patterns', patterns)
        print(f"[App Tracker] Updated patterns | Transitions: {len(self.transitions)}")
    
    def _calculate_transition_matrix(self) -> Dict:
        """Calculate transition probability matrix"""
        # Get total count for each source app
        from_app_totals = defaultdict(int)
        for (from_app, to_app), count in self.transitions.items():
            from_app_totals[from_app] += count
        
        # Calculate probabilities
        probs = {}
        for (from_app, to_app), count in self.transitions.items():
            total = from_app_totals[from_app]
            prob = count / total if total > 0 else 0
            probs[f"{from_app}->{to_app}"] = prob
        
        return probs
    
    def _calculate_time_preferences(self) -> Dict:
        """Calculate time-of-day preferences for each app"""
        prefs = {}
        
        for app, hour_counts in self.time_patterns.items():
            total = sum(hour_counts.values())
            hour_probs = {
                hour: count / total
                for hour, count in hour_counts.items()
            }
            prefs[app] = hour_probs
        
        return prefs
    
    def _calculate_usage_stats(self) -> Dict:
        """Calculate usage statistics"""
        stats = {}
        
        # Most used apps
        app_counts = defaultdict(int)
        for (from_app, _), count in self.transitions.items():
            app_counts[from_app] += count
        
        # Average duration per app
        avg_durations = {}
        for app, durations in self.app_durations.items():
            if durations:
                avg_durations[app] = np.mean(durations)
        
        stats = {
            'most_used': sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'avg_durations': avg_durations,
            'total_transitions': sum(self.transitions.values()),
            'unique_apps': len(app_counts)
        }
        
        return stats
    
    def get_transition_probability(self, from_app: str, to_app: str) -> float:
        """
        Get probability of transitioning from one app to another
        
        Args:
            from_app: Source application
            to_app: Destination application
        
        Returns:
            Probability (0-1)
        """
        transition_count = self.transitions.get((from_app, to_app), 0)
        
        # Get total transitions from source app
        total = sum(count for (f, _), count in self.transitions.items() if f == from_app)
        
        return transition_count / total if total > 0 else 0
    
    def get_time_probability(self, app: str, hour: int) -> float:
        """
        Get probability of using app at given hour
        
        Args:
            app: Application name
            hour: Hour of day (0-23)
        
        Returns:
            Probability (0-1)
        """
        hour_count = self.time_patterns[app].get(hour, 0)
        total = sum(self.time_patterns[app].values())
        
        return hour_count / total if total > 0 else 0
    
    def calculate_anomaly_score(self, current_sequence: List[str]) -> float:
        """
        Calculate how anomalous the current app sequence is
        
        Args:
            current_sequence: Recent app sequence (e.g., ["firefox", "terminal", "vscode"])
        
        Returns:
            Anomaly score (0-1, higher = more unusual)
        """
        if len(current_sequence) < 2:
            return 0.0
        
        # Calculate probability of the sequence
        sequence_prob = 1.0
        for i in range(len(current_sequence) - 1):
            from_app = current_sequence[i]
            to_app = current_sequence[i + 1]
            prob = self.get_transition_probability(from_app, to_app)
            
            # Use Laplace smoothing (assume small probability if never seen)
            prob = max(prob, 0.01)
            sequence_prob *= prob
        
        # Also check time-of-day
        current_hour = datetime.now().hour
        current_app = current_sequence[-1]
        time_prob = max(self.get_time_probability(current_app, current_hour), 0.01)
        
        # Combine probabilities (higher prob = lower anomaly)
        combined_prob = (sequence_prob * time_prob) ** (1 / len(current_sequence))
        anomaly_score = 1.0 - combined_prob
        
        return min(anomaly_score, 1.0)


if __name__ == '__main__':
    tracker = AppTracker()
    tracker.process_events()
