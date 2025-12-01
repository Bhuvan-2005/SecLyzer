use rdev::{listen, Event, EventType, Key};
use redis::Commands;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize, Deserialize, Debug)]
struct KeyboardEvent {
    #[serde(rename = "type")]
    event_type: String,
    ts: u128,  // Timestamp in microseconds
    key: String,
    event: String,  // "press" or "release"
}

fn main() {
    println!("[Keyboard Collector] Starting...");
    
    // Connect to Redis
    let redis_client = redis::Client::open("redis://127.0.0.1:6379/")
        .expect("Failed to connect to Redis");
    let mut con = redis_client.get_connection()
        .expect("Failed to get Redis connection");
    
    println!("[Keyboard Collector] Connected to Redis");
    println!("[Keyboard Collector] Listening for keyboard events (Ctrl+C to stop)");
    
    // Start listening to keyboard events
    if let Err(error) = listen(move |event| {
        match event.event_type {
            EventType::KeyPress(key) | EventType::KeyRelease(key) => {
                // Get current timestamp in microseconds
                let timestamp = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .expect("Time went backwards")
                    .as_micros();
                
                let event_name = match event.event_type {
                    EventType::KeyPress(_) => "press",
                    EventType::KeyRelease(_) => "release",
                    _ => "unknown",
                };
                
                let keyboard_event = KeyboardEvent {
                    event_type: "keystroke".to_string(),
                    ts: timestamp,
                    key: format!("{:?}", key),  // Use debug format to get key name
                    event: event_name.to_string(),
                };
                
                // Serialize to JSON
                let json = serde_json::to_string(&keyboard_event)
                    .expect("Failed to serialize event");
                
                // Publish to Redis channel
                let _: () = con.publish("seclyzer:events", json)
                    .expect("Failed to publish to Redis");
            }
            _ => {}
        }
    }) {
        eprintln!("[Keyboard Collector] Error: {:?}", error);
    }
}
