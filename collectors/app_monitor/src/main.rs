use redis::Commands;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH, Duration};
use std::thread;
use x11rb::connection::Connection;
use x11rb::protocol::xproto::*;
use x11rb::rust_connection::RustConnection;

#[derive(Serialize, Deserialize, Debug)]
struct AppEvent {
    #[serde(rename = "type")]
    event_type: String,
    ts: u128,
    app_name: String,
    window_class: String,
    event: String,  // "focus"
}

fn get_active_window_info(conn: &RustConnection, screen_num: usize) -> Option<(String, String)> {
    let screen = &conn.setup().roots[screen_num];
    
    // Get the _NET_ACTIVE_WINDOW property
    let net_active_window = conn.intern_atom(false, b"_NET_ACTIVE_WINDOW")
        .ok()?
        .reply()
        .ok()?
        .atom;
    
    let active_window = conn.get_property(
        false,
        screen.root,
        net_active_window,
        AtomEnum::WINDOW,
        0,
        1,
    ).ok()?.reply().ok()?;
    
    if active_window.value.is_empty() {
        return None;
    }
    
    let window_id = u32::from_ne_bytes(active_window.value[0..4].try_into().ok()?);
    
    // Get WM_CLASS property
    let wm_class_atom = conn.intern_atom(false, b"WM_CLASS")
        .ok()?
        .reply()
        .ok()?
        .atom;
    
    let wm_class = conn.get_property(
        false,
        window_id,
        wm_class_atom,
        AtomEnum::STRING,
        0,
        1024,
    ).ok()?.reply().ok()?;
    
    let class_str = String::from_utf8_lossy(&wm_class.value);
    let parts: Vec<&str> = class_str.split('\0').filter(|s| !s.is_empty()).collect();
    
    let app_name = parts.get(0).unwrap_or(&"Unknown").to_string();
    let window_class = parts.get(1).unwrap_or(&"Unknown").to_string();
    
    Some((app_name, window_class))
}

fn main() {
    println!("[App Monitor] Starting...");
    
    // Connect to Redis
    let redis_client = redis::Client::open("redis://127.0.0.1:6379/")
        .expect("Failed to connect to Redis");
    let mut con = redis_client.get_connection()
        .expect("Failed to get Redis connection");
    
    println!("[App Monitor] Connected to Redis");
    
    // Connect to X11
    let (conn, screen_num) = match RustConnection::connect(None) {
        Ok(conn) => conn,
        Err(e) => {
            eprintln!("[App Monitor] Failed to connect to X11: {:?}", e);
            eprintln!("[App Monitor] Make sure you're running on X11 (not Wayland)");
            return;
        }
    };
    
    println!("[App Monitor] Connected to X11");
    println!("[App Monitor] Monitoring active window (Ctrl+C to stop)");
    
    let mut last_app: Option<String> = None;
    
    loop {
        if let Some((app_name, window_class)) = get_active_window_info(&conn, screen_num) {
            // Only send event if app changed
            if last_app.as_ref() != Some(&app_name) {
                let timestamp = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .expect("Time went backwards")
                    .as_micros();
                
                let app_event = AppEvent {
                    event_type: "app".to_string(),
                    ts: timestamp,
                    app_name: app_name.clone(),
                    window_class,
                    event: "focus".to_string(),
                };
                
                let json = serde_json::to_string(&app_event)
                    .expect("Failed to serialize event");
                
                let _: () = con.publish("seclyzer:events", json)
                    .expect("Failed to publish to Redis");
                
                println!("[App Monitor] App switched to: {}", app_name);
                last_app = Some(app_name);
            }
        }
        
        // Poll every 500ms
        thread::sleep(Duration::from_millis(500));
    }
}
