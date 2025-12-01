use crate::features::{KeystrokeEvent, KeystrokeFeatureCalculator};
use std::collections::VecDeque;
use tokio::time::{interval, Duration};
use redis::aio::ConnectionManager;
use chrono::Utc;

pub struct KeystrokeExtractor {
    events: VecDeque<KeystrokeEvent>,
    feature_calculator: KeystrokeFeatureCalculator,
    window_seconds: u64,
    update_interval: u64,
}

impl KeystrokeExtractor {
    pub fn new(window_seconds: u64, update_interval: u64) -> Self {
        KeystrokeExtractor {
            events: VecDeque::with_capacity(10000),
            feature_calculator: KeystrokeFeatureCalculator::new(window_seconds),
            window_seconds,
            update_interval,
        }
    }
    
    /// Add a keystroke event to the buffer
    pub fn add_event(&mut self, timestamp: f64, key: String, event_type: String) {
        // Keep buffer bounded
        if self.events.len() >= 10000 {
            self.events.pop_front();
        }
        
        self.events.push_back(KeystrokeEvent {
            timestamp,
            key,
            event_type,
        });
    }
    
    /// Extract features from current buffer
    pub fn extract_features(&self) -> Option<serde_json::Value> {
        let events: Vec<KeystrokeEvent> = self.events.iter().cloned().collect();
        let current_time = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        
        self.feature_calculator.extract_features(&events, current_time)
    }
    
    /// Clear old events outside the window
    pub fn cleanup_old_events(&mut self) {
        let current_time = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        
        let cutoff_time = current_time - (self.window_seconds as f64 * 2.0);
        
        while let Some(front) = self.events.front() {
            if front.timestamp < cutoff_time {
                self.events.pop_front();
            } else {
                break;
            }
        }
    }
}
