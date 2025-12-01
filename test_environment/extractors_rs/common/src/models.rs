use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

/// Raw event from Redis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawEvent {
    pub event_type: String,  // "keystroke", "mouse", "app"
    pub ts: u64,             // microseconds
    #[serde(skip_serializing_if = "Option::is_none")]
    pub key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub event: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub x: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub y: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub button: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub scroll_delta: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub app_name: Option<String>,
}

/// Keystroke event
#[derive(Debug, Clone)]
pub struct KeystrokeEvent {
    pub timestamp: f64,      // seconds
    pub key: String,
    pub event_type: String,  // "press" or "release"
    pub dev_mode: bool,
}

/// Mouse event
#[derive(Debug, Clone)]
pub struct MouseEvent {
    pub timestamp: f64,
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub event_type: String,  // "move", "press", "release", "scroll"
    pub button: Option<String>,
    pub scroll_delta: Option<f64>,
    pub dev_mode: bool,
}

/// App event
#[derive(Debug, Clone)]
pub struct AppEvent {
    pub timestamp: f64,
    pub app_name: String,
    pub dev_mode: bool,
}

/// Keystroke features (140 total)
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct KeystrokeFeatures {
    pub timestamp: String,
    pub event_type: String,
    #[serde(flatten)]
    pub features: HashMap<String, f64>,
}

/// Mouse features (38 total)
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MouseFeatures {
    pub timestamp: String,
    pub event_type: String,
    #[serde(flatten)]
    pub features: HashMap<String, f64>,
}

/// App transition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppTransition {
    pub from_app: String,
    pub to_app: String,
    pub duration_ms: i64,
    pub timestamp: String,
}

/// InfluxDB write request
#[derive(Debug, Clone, Serialize)]
pub struct InfluxPoint {
    pub measurement: String,
    pub tags: HashMap<String, String>,
    pub fields: HashMap<String, f64>,
    pub timestamp: i64,  // nanoseconds
}
