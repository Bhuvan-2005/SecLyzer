use crate::features::{MouseEvent, MouseFeatureCalculator};
use std::collections::VecDeque;

pub struct MouseExtractor {
    events: VecDeque<MouseEvent>,
    feature_calculator: MouseFeatureCalculator,
    window_seconds: u64,
}

impl MouseExtractor {
    pub fn new(window_seconds: u64) -> Self {
        MouseExtractor {
            events: VecDeque::with_capacity(50000),
            feature_calculator: MouseFeatureCalculator::new(window_seconds),
            window_seconds,
        }
    }
    
    /// Add a mouse event to the buffer
    pub fn add_event(
        &mut self,
        timestamp: f64,
        x: Option<f64>,
        y: Option<f64>,
        event_type: String,
        button: Option<String>,
        scroll_delta: Option<f64>,
    ) {
        if self.events.len() >= 50000 {
            self.events.pop_front();
        }
        
        self.events.push_back(MouseEvent {
            timestamp,
            x,
            y,
            event_type,
            button,
            scroll_delta,
        });
    }
    
    /// Extract features from current buffer
    pub fn extract_features(&self) -> Option<serde_json::Value> {
        let events: Vec<MouseEvent> = self.events.iter().cloned().collect();
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
