use keystroke_extractor::KeystrokeExtractor;
use common::{init_logging, AppContext};
use tokio::time::{interval, Duration};
use std::time::{SystemTime, UNIX_EPOCH};
use tracing::{info, error};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    init_logging();
    info!("Keystroke Extractor starting");
    
    let ctx = AppContext::new().await?;
    let config = ctx.config.clone();
    
    let mut extractor = KeystrokeExtractor::new(
        config.window_seconds,
        config.update_interval,
    );
    
    let mut update_interval = interval(Duration::from_secs(config.update_interval));
    let mut cleanup_interval = interval(Duration::from_secs(60));
    
    info!("Keystroke Extractor initialized and ready");
    
    // Example: simulate keystroke events for testing
    loop {
        tokio::select! {
            _ = update_interval.tick() => {
                if let Some(features) = extractor.extract_features() {
                    info!("Extracted keystroke features");
                    
                    // Publish to Redis
                    if let Err(e) = ctx.redis.publish_features(
                        "seclyzer:features:keystroke",
                        &features,
                    ).await {
                        error!("Failed to publish features: {}", e);
                    }
                }
            }
            _ = cleanup_interval.tick() => {
                extractor.cleanup_old_events();
                info!("Cleaned up old events");
            }
        }
    }
}
