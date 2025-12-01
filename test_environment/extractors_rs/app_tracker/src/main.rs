use app_tracker::AppTracker;
use common::{init_logging, AppContext};
use tokio::time::{interval, Duration};
use tracing::{info, error};
use std::sync::Arc;
use tokio::sync::Mutex;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    init_logging();
    info!("App Tracker starting");
    
    let ctx = AppContext::new().await?;
    let config = ctx.config.clone();
    
    let tracker = Arc::new(Mutex::new(AppTracker::new()));
    
    let mut update_interval = interval(Duration::from_secs(60));
    
    info!("App Tracker initialized and ready");
    
    loop {
        tokio::select! {
            _ = update_interval.tick() => {
                let tracker_locked = tracker.lock().await;
                let state = tracker_locked.get_state();
                
                info!("Updated app patterns");
                
                // Publish state to Redis
                if let Err(e) = ctx.redis.publish_features(
                    "seclyzer:features:app",
                    &state,
                ).await {
                    error!("Failed to publish app state: {}", e);
                }
            }
        }
    }
}
