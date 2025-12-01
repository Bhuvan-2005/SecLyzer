#!/usr/bin/env python3
"""
Event Monitor - Simple utility to watch Redis events in real-time
This is for testing Phase 1 collectors
"""

import redis
import json
import sys
from datetime import datetime
from collections import defaultdict

def format_timestamp(ts_microseconds):
    """Convert microseconds timestamp to readable format"""
    ts_seconds = ts_microseconds / 1_000_000
    return datetime.fromtimestamp(ts_seconds).strftime('%H:%M:%S.%f')[:-3]

def main():
    print("="*60)
    print("SecLyzer Event Monitor")
    print("="*60)
    print("Connecting to Redis...")
    
    try:
        r = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✓ Connected to Redis\n")
    except redis.ConnectionError:
        print("✗ Failed to connect to Redis")
        print("  Make sure Redis is running: sudo systemctl start redis-server")
        sys.exit(1)
    
    print("Listening for events on 'seclyzer:events' channel...")
    print("Press Ctrl+C to stop\n")
    print("-"*60)
    
    # Subscribe to events
    pubsub = r.pubsub()
    pubsub.subscribe('seclyzer:events')
    
    # Statistics
    stats = defaultdict(int)
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    event = json.loads(message['data'])
                    event_type = event.get('type', 'unknown')
                    timestamp = event.get('ts', 0)
                    
                    stats[event_type] += 1
                    
                    if event_type == 'keystroke':
                        print(f"[{format_timestamp(timestamp)}] KEYSTROKE: {event['key']} ({event['event']})")
                    
                    elif event_type == 'mouse':
                        if event['event'] == 'move':
                            # Only print every 10th move event to avoid spam
                            if stats['mouse'] % 10 == 0:
                                print(f"[{format_timestamp(timestamp)}] MOUSE MOVE: x={event.get('x', 0):.0f}, y={event.get('y', 0):.0f}")
                        elif event['event'] in ['press', 'release']:
                            print(f"[{format_timestamp(timestamp)}] MOUSE {event['event'].upper()}: {event.get('button', 'unknown')}")
                        elif event['event'] == 'scroll':
                            print(f"[{format_timestamp(timestamp)}] MOUSE SCROLL: delta={event.get('scroll_delta', 0)}")
                    
                    elif event_type == 'app':
                        print(f"[{format_timestamp(timestamp)}] APP SWITCH: {event['app_name']} ({event['window_class']})")
                    
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON received")
                except Exception as e:
                    print(f"Error processing event: {e}")
    
    except KeyboardInterrupt:
        print("\n" + "-"*60)
        print("\n📊 Event Statistics:")
        print(f"  Keystroke events: {stats.get('keystroke', 0)}")
        print(f"  Mouse events: {stats.get('mouse', 0)}")
        print(f"  App events: {stats.get('app', 0)}")
        print(f"  Total: {sum(stats.values())}")
        print("\nMonitor stopped.")

if __name__ == '__main__':
    main()
