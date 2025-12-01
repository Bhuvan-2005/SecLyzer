pub mod redis_client;
pub mod influx_client;
pub mod models;
pub mod config;
pub mod logger;

pub use redis_client::RedisClient;
pub use influx_client::InfluxClient;
pub use config::Config;
pub use models::*;

use anyhow::Result;
use std::sync::Arc;

/// Initialize logging system
pub fn init_logging() {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();
}

/// Application context holding shared resources
pub struct AppContext {
    pub redis: Arc<RedisClient>,
    pub influx: Arc<InfluxClient>,
    pub config: Arc<Config>,
}

impl AppContext {
    pub async fn new() -> Result<Self> {
        let config = Arc::new(Config::from_env()?);
        tracing::info!("Loaded configuration");
        
        let redis = Arc::new(RedisClient::new(config.as_ref()).await?);
        tracing::info!("Connected to Redis");
        
        let influx = Arc::new(InfluxClient::new(config.as_ref()).await?);
        tracing::info!("Connected to InfluxDB");
        
        Ok(AppContext {
            redis,
            influx,
            config,
        })
    }
}
