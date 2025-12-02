use rdev::{listen, EventType};
use redis::Commands;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize, Deserialize, Debug)]
struct MouseEvent {
    #[serde(rename = "type")]
    event_type: String,
    ts: u128,  // Timestamp in microseconds
    x: Option<f64>,
    y: Option<f64>,
    event: String,  // "move", "click", "release", "scroll"
    button: Option<String>,
    scroll_delta: Option<i64>,
}

fn main() {
    println!("[Mouse Collector] Starting...");
    
    // Connect to Redis
    let redis_client = redis::Client::open("redis://127.0.0.1:6379/")
        .expect("Failed to connect to Redis");
    let mut con = redis_client.get_connection()
        .expect("Failed to get Redis connection");
    
    println!("[Mouse Collector] Connected to Redis");
    println!("[Mouse Collector] Listening for mouse events (Ctrl+C to stop)");
    
    // Start listening to mouse events
    if let Err(error) = listen(move |event| {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("Time went backwards")
            .as_micros();
        
        let mouse_event = match event.event_type {
            EventType::MouseMove { x, y } => {
                Some(MouseEvent {
                    event_type: "mouse".to_string(),
                    ts: timestamp,
                    x: Some(x),
                    y: Some(y),
                    event: "move".to_string(),
                    button: None,
                    scroll_delta: None,
                })
            }
            EventType::ButtonPress(button) => {
                Some(MouseEvent {
                    event_type: "mouse".to_string(),
                    ts: timestamp,
                    x: None,
                    y: None,
                    event: "press".to_string(),
                    button: Some(format!("{:?}", button)),
                    scroll_delta: None,
                })
            }
            EventType::ButtonRelease(button) => {
                Some(MouseEvent {
                    event_type: "mouse".to_string(),
                    ts: timestamp,
                    x: None,
                    y: None,
                    event: "release".to_string(),
                    button: Some(format!("{:?}", button)),
                    scroll_delta: None,
                })
            }
            EventType::Wheel { delta_x: _, delta_y } => {
                Some(MouseEvent {
                    event_type: "mouse".to_string(),
                    ts: timestamp,
                    x: None,
                    y: None,
                    event: "scroll".to_string(),
                    button: None,
                    scroll_delta: Some(delta_y),
                })
            }
            _ => None,
        };
        
        if let Some(event) = mouse_event {
            // Serialize to JSON
            let json = serde_json::to_string(&event)
                .expect("Failed to serialize event");
            
            // Publish to Redis channel
            let _: () = con.publish("seclyzer:events", json)
                .expect("Failed to publish to Redis");
        }
    }) {
        eprintln!("[Mouse Collector] Error: {:?}", error);
    }
}
