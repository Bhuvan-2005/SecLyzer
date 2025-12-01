use std::collections::HashMap;
use std::f64::consts::PI;

#[derive(Debug, Clone)]
pub struct MouseEvent {
    pub timestamp: f64,
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub event_type: String, // "move", "press", "release", "scroll"
    pub button: Option<String>,
    pub scroll_delta: Option<f64>,
}

pub struct MouseFeatureCalculator {
    window_seconds: u64,
}

impl MouseFeatureCalculator {
    pub fn new(window_seconds: u64) -> Self {
        MouseFeatureCalculator { window_seconds }
    }
    
    /// Extract 38 mouse features from events
    pub fn extract_features(
        &self,
        events: &[MouseEvent],
        current_time: f64,
    ) -> Option<serde_json::Value> {
        let cutoff_time = current_time - self.window_seconds as f64;
        let recent: Vec<&MouseEvent> = events
            .iter()
            .filter(|e| e.timestamp > cutoff_time)
            .collect();
        
        if recent.len() < 50 {
            return None;
        }
        
        let mut features = HashMap::new();
        
        // Separate events by type
        let movements: Vec<&MouseEvent> = recent
            .iter()
            .filter(|e| e.event_type == "move" && e.x.is_some())
            .copied()
            .collect();
        
        let clicks: Vec<&MouseEvent> = recent
            .iter()
            .filter(|e| e.event_type == "press" || e.event_type == "release")
            .copied()
            .collect();
        
        let scrolls: Vec<&MouseEvent> = recent
            .iter()
            .filter(|e| e.event_type == "scroll")
            .copied()
            .collect();
        
        // Calculate movement features (20 features)
        if movements.len() > 2 {
            let movement_features = self.calculate_movement_features(&movements);
            features.extend(movement_features);
        } else {
            for i in 0..20 {
                features.insert(format!("move_{}", i), 0.0);
            }
        }
        
        // Calculate click features (10 features)
        if !clicks.is_empty() {
            let click_features = self.calculate_click_features(&clicks);
            features.extend(click_features);
        } else {
            for i in 0..10 {
                features.insert(format!("click_{}", i), 0.0);
            }
        }
        
        // Calculate scroll features (8 features)
        if !scrolls.is_empty() {
            let scroll_features = self.calculate_scroll_features(&scrolls);
            features.extend(scroll_features);
        } else {
            for i in 0..8 {
                features.insert(format!("scroll_{}", i), 0.0);
            }
        }
        
        features.insert("dev_mode".to_string(), 0.0);
        
        Some(serde_json::to_value(features).unwrap())
    }
    
    fn calculate_movement_features(&self, movements: &[&MouseEvent]) -> HashMap<String, f64> {
        let mut features = HashMap::new();
        
        let x: Vec<f64> = movements.iter().filter_map(|e| e.x).collect();
        let y: Vec<f64> = movements.iter().filter_map(|e| e.y).collect();
        let t: Vec<f64> = movements.iter().map(|e| e.timestamp).collect();
        
        if x.len() < 2 || y.len() < 2 {
            for i in 0..20 {
                features.insert(format!("move_{}", i), 0.0);
            }
            return features;
        }
        
        // Calculate distances
        let mut distances = Vec::new();
        for i in 0..x.len() - 1 {
            let dx = x[i + 1] - x[i];
            let dy = y[i + 1] - y[i];
            let dist = (dx * dx + dy * dy).sqrt();
            distances.push(dist);
        }
        
        // Time deltas
        let mut dt = Vec::new();
        for i in 0..t.len() - 1 {
            let delta = t[i + 1] - t[i];
            dt.push(delta.max(0.001));
        }
        
        // Velocity (pixels/second)
        let velocities: Vec<f64> = distances
            .iter()
            .zip(&dt)
            .map(|(d, dt)| d / dt)
            .filter(|v| v < &10000.0)
            .collect();
        
        // Acceleration
        let mut accelerations = Vec::new();
        if velocities.len() > 1 {
            for i in 0..velocities.len() - 1 {
                let dv = velocities[i + 1] - velocities[i];
                let accel = dv / dt[i];
                if accel.abs() < 100000.0 {
                    accelerations.push(accel);
                }
            }
        }
        
        // Direction changes (angles)
        let mut angle_changes = Vec::new();
        for i in 0..x.len() - 1 {
            let dx = x[i + 1] - x[i];
            let dy = y[i + 1] - y[i];
            let angle = dy.atan2(dx);
            if i > 0 {
                let prev_dx = x[i] - x[i - 1];
                let prev_dy = y[i] - y[i - 1];
                let prev_angle = prev_dy.atan2(prev_dx);
                let angle_diff = (angle - prev_angle).abs();
                angle_changes.push(angle_diff);
            }
        }
        
        // Curvature
        let total_distance: f64 = distances.iter().sum();
        let straight_distance = ((x[x.len() - 1] - x[0]).powi(2) + (y[y.len() - 1] - y[0]).powi(2)).sqrt();
        let curvature = 1.0 - (straight_distance / total_distance.max(1.0));
        
        // Jerk
        let mut jerk = Vec::new();
        if accelerations.len() > 1 {
            for i in 0..accelerations.len() - 1 {
                let da = accelerations[i + 1] - accelerations[i];
                let j = da / dt[i];
                if j.abs() < 1000000.0 {
                    jerk.push(j);
                }
            }
        }
        
        // Populate features
        features.insert("move_0".to_string(), self.mean(&velocities)); // velocity mean
        features.insert("move_1".to_string(), self.std_dev(&velocities)); // velocity std
        features.insert("move_2".to_string(), self.max(&velocities)); // velocity max
        features.insert("move_3".to_string(), self.median(&velocities)); // velocity median
        
        features.insert("move_4".to_string(), self.mean(&accelerations.iter().map(|a| a.abs()).collect::<Vec<_>>())); // accel mean
        features.insert("move_5".to_string(), self.std_dev(&accelerations)); // accel std
        features.insert("move_6".to_string(), self.max(&accelerations.iter().map(|a| a.abs()).collect::<Vec<_>>())); // accel max
        
        features.insert("move_7".to_string(), curvature);
        features.insert("move_8".to_string(), self.mean(&angle_changes)); // angle change mean
        features.insert("move_9".to_string(), self.std_dev(&angle_changes)); // angle change std
        
        features.insert("move_10".to_string(), self.mean(&jerk.iter().map(|j| j.abs()).collect::<Vec<_>>())); // jerk mean
        features.insert("move_11".to_string(), self.std_dev(&jerk)); // jerk std
        
        features.insert("move_12".to_string(), total_distance); // total distance
        features.insert("move_13".to_string(), straight_distance); // straight distance
        features.insert("move_14".to_string(), total_distance / movements.len() as f64); // avg distance per sample
        
        let idle_count = dt.iter().filter(|&&d| d > 0.1).count();
        features.insert("move_15".to_string(), idle_count as f64 / dt.len() as f64); // idle fraction
        features.insert("move_16".to_string(), self.mean(&dt)); // mean time between samples
        features.insert("move_17".to_string(), self.std_dev(&dt)); // std time between samples
        
        features.insert("move_18".to_string(), straight_distance / total_distance.max(1.0)); // efficiency
        features.insert("move_19".to_string(), movements.len() as f64 / self.window_seconds as f64); // movement frequency
        
        features
    }
    
    fn calculate_click_features(&self, clicks: &[&MouseEvent]) -> HashMap<String, f64> {
        let mut features = HashMap::new();
        
        let presses: Vec<&MouseEvent> = clicks
            .iter()
            .filter(|e| e.event_type == "press")
            .copied()
            .collect();
        
        let releases: Vec<&MouseEvent> = clicks
            .iter()
            .filter(|e| e.event_type == "release")
            .copied()
            .collect();
        
        // Click durations
        let mut click_durations = Vec::new();
        let mut press_times: HashMap<String, f64> = HashMap::new();
        
        for press in &presses {
            if let Some(button) = &press.button {
                press_times.insert(button.clone(), press.timestamp);
            }
        }
        
        for release in &releases {
            if let Some(button) = &release.button {
                if let Some(&press_time) = press_times.get(button) {
                    let duration = (release.timestamp - press_time) * 1000.0;
                    if duration > 0.0 && duration < 5000.0 {
                        click_durations.push(duration);
                    }
                }
            }
        }
        
        // Count by button
        let left_clicks = presses.iter().filter(|c| c.button.as_ref().map_or(false, |b| b == "Left")).count();
        let right_clicks = presses.iter().filter(|c| c.button.as_ref().map_or(false, |b| b == "Right")).count();
        let middle_clicks = presses.iter().filter(|c| c.button.as_ref().map_or(false, |b| b == "Middle")).count();
        
        // Double-click detection (within 500ms)
        let mut double_clicks = 0;
        let mut sorted_presses = presses.clone();
        sorted_presses.sort_by(|a, b| a.timestamp.partial_cmp(&b.timestamp).unwrap_or(std::cmp::Ordering::Equal));
        for i in 0..sorted_presses.len().saturating_sub(1) {
            if (sorted_presses[i + 1].timestamp - sorted_presses[i].timestamp) < 0.5 {
                double_clicks += 1;
            }
        }
        
        features.insert("click_0".to_string(), self.mean(&click_durations));
        features.insert("click_1".to_string(), self.std_dev(&click_durations));
        features.insert("click_2".to_string(), left_clicks as f64);
        features.insert("click_3".to_string(), right_clicks as f64);
        features.insert("click_4".to_string(), middle_clicks as f64);
        
        let total_clicks = left_clicks + right_clicks + middle_clicks;
        features.insert("click_5".to_string(), left_clicks as f64 / total_clicks.max(1) as f64);
        features.insert("click_6".to_string(), double_clicks as f64);
        features.insert("click_7".to_string(), double_clicks as f64 / presses.len().max(1) as f64);
        features.insert("click_8".to_string(), presses.len() as f64 / self.window_seconds as f64);
        features.insert("click_9".to_string(), self.median(&click_durations));
        
        features
    }
    
    fn calculate_scroll_features(&self, scrolls: &[&MouseEvent]) -> HashMap<String, f64> {
        let mut features = HashMap::new();
        
        let deltas: Vec<f64> = scrolls
            .iter()
            .filter_map(|e| e.scroll_delta)
            .collect();
        
        if deltas.is_empty() {
            for i in 0..8 {
                features.insert(format!("scroll_{}", i), 0.0);
            }
            return features;
        }
        
        let up_scrolls: Vec<f64> = deltas.iter().filter(|&&d| d > 0.0).copied().collect();
        let down_scrolls: Vec<f64> = deltas.iter().filter(|&&d| d < 0.0).copied().collect();
        
        let times: Vec<f64> = scrolls.iter().map(|e| e.timestamp).collect();
        let mut intervals = Vec::new();
        for i in 0..times.len().saturating_sub(1) {
            intervals.push(times[i + 1] - times[i]);
        }
        
        features.insert("scroll_0".to_string(), self.mean(&deltas.iter().map(|d| d.abs()).collect::<Vec<_>>()));
        features.insert("scroll_1".to_string(), self.std_dev(&deltas));
        features.insert("scroll_2".to_string(), up_scrolls.len() as f64);
        features.insert("scroll_3".to_string(), down_scrolls.len() as f64);
        features.insert("scroll_4".to_string(), up_scrolls.len() as f64 / deltas.len() as f64);
        features.insert("scroll_5".to_string(), scrolls.len() as f64 / self.window_seconds as f64);
        features.insert("scroll_6".to_string(), self.mean(&intervals));
        features.insert("scroll_7".to_string(), self.std_dev(&intervals));
        
        features
    }
    
    // Utility statistics
    fn mean(&self, values: &[f64]) -> f64 {
        if values.is_empty() { 0.0 } else { values.iter().sum::<f64>() / values.len() as f64 }
    }
    
    fn std_dev(&self, values: &[f64]) -> f64 {
        if values.len() < 2 { return 0.0; }
        let mean = self.mean(values);
        let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64;
        variance.sqrt()
    }
    
    fn min(&self, values: &[f64]) -> f64 {
        values.iter().cloned().fold(f64::INFINITY, f64::min)
    }
    
    fn max(&self, values: &[f64]) -> f64 {
        values.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
    }
    
    fn median(&self, values: &[f64]) -> f64 {
        if values.is_empty() { return 0.0; }
        let mut sorted = values.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let mid = sorted.len() / 2;
        if sorted.len() % 2 == 0 {
            (sorted[mid - 1] + sorted[mid]) / 2.0
        } else {
            sorted[mid]
        }
    }
}
