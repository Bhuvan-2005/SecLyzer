use mouse_extractor::MouseExtractor;
use common::{init_logging, AppContext};
use tokio::time::{interval, Duration};
use tracing::{info, error};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    init_logging();
    info!("Mouse Extractor starting");
    
    let ctx = AppContext::new().await?;
    let config = ctx.config.clone();
    
    let mut extractor = MouseExtractor::new(config.window_seconds);
    
    let mut update_interval = interval(Duration::from_secs(config.update_interval));
    let mut cleanup_interval = interval(Duration::from_secs(60));
    
    info!("Mouse Extractor initialized and ready");
    
    loop {
        tokio::select! {
            _ = update_interval.tick() => {
                if let Some(features) = extractor.extract_features() {
                    info!("Extracted mouse features");
                    
                    if let Err(e) = ctx.redis.publish_features(
                        "seclyzer:features:mouse",
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
