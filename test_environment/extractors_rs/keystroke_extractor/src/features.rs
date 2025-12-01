use std::collections::{HashMap, VecDeque};
use serde_json::json;

#[derive(Debug, Clone)]
pub struct KeystrokeEvent {
    pub timestamp: f64,
    pub key: String,
    pub event_type: String, // "press" or "release"
}

pub struct KeystrokeFeatureCalculator {
    window_seconds: u64,
}

impl KeystrokeFeatureCalculator {
    pub fn new(window_seconds: u64) -> Self {
        KeystrokeFeatureCalculator { window_seconds }
    }
    
    /// Extract 140 keystroke features from events
    pub fn extract_features(
        &self,
        events: &[KeystrokeEvent],
        current_time: f64,
    ) -> Option<serde_json::Value> {
        let cutoff_time = current_time - self.window_seconds as f64;
        let recent: Vec<&KeystrokeEvent> = events
            .iter()
            .filter(|e| e.timestamp > cutoff_time)
            .collect();
        
        if recent.len() < 10 {
            return None;
        }
        
        let mut features = HashMap::new();
        
        // Calculate dwell times (8 features)
        let dwell_times = self.calculate_dwell_times(&recent);
        if !dwell_times.is_empty() {
            features.insert("dwell_mean".to_string(), self.mean(&dwell_times));
            features.insert("dwell_std".to_string(), self.std_dev(&dwell_times));
            features.insert("dwell_min".to_string(), self.min(&dwell_times));
            features.insert("dwell_max".to_string(), self.max(&dwell_times));
            features.insert("dwell_median".to_string(), self.median(&dwell_times));
            features.insert("dwell_q25".to_string(), self.percentile(&dwell_times, 25));
            features.insert("dwell_q75".to_string(), self.percentile(&dwell_times, 75));
            features.insert("dwell_range".to_string(), self.max(&dwell_times) - self.min(&dwell_times));
        }
        
        // Calculate flight times (8 features)
        let flight_times = self.calculate_flight_times(&recent);
        if !flight_times.is_empty() {
            features.insert("flight_mean".to_string(), self.mean(&flight_times));
            features.insert("flight_std".to_string(), self.std_dev(&flight_times));
            features.insert("flight_min".to_string(), self.min(&flight_times));
            features.insert("flight_max".to_string(), self.max(&flight_times));
            features.insert("flight_median".to_string(), self.median(&flight_times));
            features.insert("flight_q25".to_string(), self.percentile(&flight_times, 25));
            features.insert("flight_q75".to_string(), self.percentile(&flight_times, 75));
            features.insert("flight_range".to_string(), self.max(&flight_times) - self.min(&flight_times));
        }
        
        // Calculate digraph features (20 features)
        let digraphs = self.calculate_digraphs(&recent);
        for (i, digraph) in digraphs.iter().enumerate().take(20) {
            features.insert(format!("digraph_{}_mean", i), *digraph);
        }
        // Pad with zeros
        for i in digraphs.len()..20 {
            features.insert(format!("digraph_{}_mean", i), 0.0);
        }
        
        // Calculate error patterns (4 features)
        let errors = self.calculate_error_patterns(&recent);
        features.extend(errors);
        
        // Calculate rhythm features (8 features)
        let rhythm = self.calculate_rhythm(&recent);
        features.extend(rhythm);
        
        // Add metadata
        let total_keys = recent.iter().filter(|e| e.event_type == "press").count() as f64;
        features.insert("total_keys".to_string(), total_keys);
        features.insert("dev_mode".to_string(), 0.0);
        
        Some(serde_json::to_value(features).unwrap())
    }
    
    fn calculate_dwell_times(&self, events: &[&KeystrokeEvent]) -> Vec<f64> {
        let mut times = Vec::new();
        let mut key_presses: HashMap<String, f64> = HashMap::new();
        
        for event in events {
            if event.event_type == "press" {
                key_presses.insert(event.key.clone(), event.timestamp);
            } else if event.event_type == "release" {
                if let Some(press_time) = key_presses.get(&event.key) {
                    let dwell = (event.timestamp - press_time) * 1000.0;
                    if dwell > 0.0 && dwell < 1000.0 {
                        times.push(dwell);
                    }
                    key_presses.remove(&event.key);
                }
            }
        }
        times
    }
    
    fn calculate_flight_times(&self, events: &[&KeystrokeEvent]) -> Vec<f64> {
        let mut times = Vec::new();
        let presses: Vec<f64> = events
            .iter()
            .filter(|e| e.event_type == "press")
            .map(|e| e.timestamp)
            .collect();
        
        for i in 0..presses.len().saturating_sub(1) {
            let flight = (presses[i + 1] - presses[i]) * 1000.0;
            if flight > 0.0 && flight < 2000.0 {
                times.push(flight);
            }
        }
        times
    }
    
    fn calculate_digraphs(&self, events: &[&KeystrokeEvent]) -> Vec<f64> {
        let mut times = Vec::new();
        let presses: Vec<&KeystrokeEvent> = events
            .iter()
            .filter(|e| e.event_type == "press")
            .copied()
            .collect();
        
        for i in 0..presses.len().saturating_sub(1) {
            let time_diff = (presses[i + 1].timestamp - presses[i].timestamp) * 1000.0;
            if time_diff > 0.0 && time_diff < 2000.0 {
                times.push(time_diff);
            }
        }
        times.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        times.truncate(20);
        times
    }
    
    fn calculate_error_patterns(&self, events: &[&KeystrokeEvent]) -> HashMap<String, f64> {
        let mut features = HashMap::new();
        let total_keys = events.iter().filter(|e| e.event_type == "press").count();
        let backspace_count = events
            .iter()
            .filter(|e| e.event_type == "press" && (e.key.contains("BackSpace") || e.key.contains("Delete")))
            .count();
        
        features.insert(
            "backspace_frequency".to_string(),
            backspace_count as f64 / total_keys.max(1) as f64,
        );
        features.insert("backspace_count".to_string(), backspace_count as f64);
        features.insert(
            "correction_rate".to_string(),
            backspace_count as f64 / (total_keys - backspace_count).max(1) as f64,
        );
        features.insert(
            "clean_typing_ratio".to_string(),
            (total_keys - backspace_count) as f64 / total_keys.max(1) as f64,
        );
        features
    }
    
    fn calculate_rhythm(&self, events: &[&KeystrokeEvent]) -> HashMap<String, f64> {
        let mut features = HashMap::new();
        let mut intervals = Vec::new();
        let presses: Vec<f64> = events
            .iter()
            .filter(|e| e.event_type == "press")
            .map(|e| e.timestamp)
            .collect();
        
        for i in 0..presses.len().saturating_sub(1) {
            let interval = (presses[i + 1] - presses[i]) * 1000.0;
            if interval > 0.0 && interval < 5000.0 {
                intervals.push(interval);
            }
        }
        
        if intervals.is_empty() {
            for i in 0..8 {
                features.insert(format!("rhythm_{}", i), 0.0);
            }
            return features;
        }
        
        let burst_threshold = self.median(&intervals);
        let bursts: Vec<f64> = intervals.iter().filter(|&&i| i < burst_threshold).copied().collect();
        let pauses: Vec<f64> = intervals.iter().filter(|&&i| i >= burst_threshold).copied().collect();
        
        features.insert(
            "rhythm_consistency".to_string(),
            1.0 - (self.std_dev(&intervals) / self.mean(&intervals).max(1.0)),
        );
        features.insert("burst_frequency".to_string(), bursts.len() as f64 / intervals.len() as f64);
        features.insert("pause_frequency".to_string(), pauses.len() as f64 / intervals.len() as f64);
        features.insert("avg_burst_speed".to_string(), if bursts.is_empty() { 0.0 } else { self.mean(&bursts) });
        features.insert("avg_pause_duration".to_string(), if pauses.is_empty() { 0.0 } else { self.mean(&pauses) });
        features.insert("rhythm_variation".to_string(), self.std_dev(&intervals));
        features.insert("typing_speed_wpm".to_string(), 60000.0 / self.mean(&intervals).max(1.0) / 5.0);
        features.insert("rhythm_stability".to_string(), 1.0 / (1.0 + self.variance(&intervals)));
        features
    }
    
    // Utility statistics functions
    fn mean(&self, values: &[f64]) -> f64 {
        if values.is_empty() { 0.0 } else { values.iter().sum::<f64>() / values.len() as f64 }
    }
    
    fn std_dev(&self, values: &[f64]) -> f64 {
        let mean = self.mean(values);
        let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64;
        variance.sqrt()
    }
    
    fn variance(&self, values: &[f64]) -> f64 {
        let mean = self.mean(values);
        values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64
    }
    
    fn min(&self, values: &[f64]) -> f64 {
        values.iter().cloned().fold(f64::INFINITY, f64::min)
    }
    
    fn max(&self, values: &[f64]) -> f64 {
        values.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
    }
    
    fn median(&self, values: &[f64]) -> f64 {
        let mut sorted = values.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let mid = sorted.len() / 2;
        if sorted.len() % 2 == 0 {
            (sorted[mid - 1] + sorted[mid]) / 2.0
        } else {
            sorted[mid]
        }
    }
    
    fn percentile(&self, values: &[f64], p: usize) -> f64 {
        let mut sorted = values.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let idx = (sorted.len() * p / 100).max(0).min(sorted.len() - 1);
        sorted[idx]
    }
}
