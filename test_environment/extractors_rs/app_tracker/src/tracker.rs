use std::collections::{HashMap, VecDeque};
use chrono::{Utc, Timelike};

#[derive(Debug, Clone)]
pub struct AppEvent {
    pub timestamp: f64,
    pub app_name: String,
}

pub struct AppTracker {
    current_app: Option<String>,
    current_app_start: Option<f64>,
    transitions: HashMap<(String, String), u32>,
    app_durations: HashMap<String, Vec<f64>>,
    time_patterns: HashMap<String, HashMap<u32, u32>>,
    recent_events: VecDeque<AppEvent>,
}

impl AppTracker {
    pub fn new() -> Self {
        AppTracker {
            current_app: None,
            current_app_start: None,
            transitions: HashMap::new(),
            app_durations: HashMap::new(),
            time_patterns: HashMap::new(),
            recent_events: VecDeque::with_capacity(1000),
        }
    }
    
    /// Handle app switch event
    pub fn handle_app_switch(&mut self, app_name: String, timestamp: f64) {
        let now = Utc::now();
        let hour = now.hour() as u32;
        
        // Record transition if switching from a previous app
        if let Some(prev_app) = self.current_app.take() {
            if prev_app != app_name {
                if let Some(start_time) = self.current_app_start {
                    let duration = timestamp - start_time;
                    
                    // Record transition
                    let key = (prev_app.clone(), app_name.clone());
                    *self.transitions.entry(key).or_insert(0) += 1;
                    
                    // Record duration
                    self.app_durations
                        .entry(prev_app.clone())
                        .or_insert_with(Vec::new)
                        .push(duration);
                }
            }
        }
        
        // Update current app
        self.current_app = Some(app_name.clone());
        self.current_app_start = Some(timestamp);
        
        // Record time pattern
        self.time_patterns
            .entry(app_name.clone())
            .or_insert_with(HashMap::new)
            .entry(hour)
            .and_modify(|c| *c += 1)
            .or_insert(1);
        
        // Add to recent events
        if self.recent_events.len() >= 1000 {
            self.recent_events.pop_front();
        }
        self.recent_events.push_back(AppEvent {
            timestamp,
            app_name,
        });
    }
    
    /// Calculate transition probabilities
    pub fn calculate_transition_matrix(&self) -> HashMap<String, f64> {
        let mut from_totals: HashMap<String, u32> = HashMap::new();
        
        for ((from_app, _to_app), count) in &self.transitions {
            *from_totals.entry(from_app.clone()).or_insert(0) += count;
        }
        
        let mut probs = HashMap::new();
        for ((from_app, to_app), count) in &self.transitions {
            let total = from_totals.get(from_app).copied().unwrap_or(1);
            let prob = *count as f64 / total as f64;
            probs.insert(format!("{}->{}", from_app, to_app), prob);
        }
        
        probs
    }
    
    /// Calculate time-of-day preferences
    pub fn calculate_time_preferences(&self) -> HashMap<String, HashMap<u32, f64>> {
        let mut prefs = HashMap::new();
        
        for (app, hour_counts) in &self.time_patterns {
            let total: u32 = hour_counts.values().sum();
            let mut hour_probs = HashMap::new();
            
            for (hour, count) in hour_counts {
                hour_probs.insert(*hour, *count as f64 / total as f64);
            }
            
            prefs.insert(app.clone(), hour_probs);
        }
        
        prefs
    }
    
    /// Calculate usage statistics
    pub fn calculate_usage_stats(&self) -> serde_json::Value {
        let mut stats = serde_json::json!({});
        
        for (app, durations) in &self.app_durations {
            if durations.is_empty() {
                continue;
            }
            
            let mean = durations.iter().sum::<f64>() / durations.len() as f64;
            let total_time: f64 = durations.iter().sum();
            
            stats[app.as_str()] = serde_json::json!({
                "total_time_seconds": total_time,
                "avg_session_seconds": mean,
                "session_count": durations.len(),
            });
        }
        
        stats
    }
    
    /// Get current state as JSON
    pub fn get_state(&self) -> serde_json::Value {
        serde_json::json!({
            "current_app": self.current_app,
            "transition_matrix": self.calculate_transition_matrix(),
            "time_preferences": self.calculate_time_preferences(),
            "usage_stats": self.calculate_usage_stats(),
            "transition_count": self.transitions.len(),
        })
    }
}

impl Default for AppTracker {
    fn default() -> Self {
        Self::new()
    }
}
