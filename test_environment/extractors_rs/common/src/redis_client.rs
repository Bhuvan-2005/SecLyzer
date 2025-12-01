use crate::config::Config;
use anyhow::Result;
use redis::aio::ConnectionManager;
use redis::{AsyncCommands, Client};
use serde_json::json;

pub struct RedisClient {
    manager: ConnectionManager,
}

impl RedisClient {
    pub async fn new(config: &Config) -> Result<Self> {
        let client_url = if let Some(password) = &config.redis_password {
            format!(
                "redis://:{password}@{}:{}",
                config.redis_host, config.redis_port
            )
        } else {
            format!("redis://{}:{}", config.redis_host, config.redis_port)
        };
        
        let client = Client::open(client_url)?;
        let manager = ConnectionManager::new(client).await?;
        
        // Test connection
        let mut conn = manager.clone();
        let pong: String = redis::cmd("PING").query_async(&mut conn).await?;
        tracing::info!("Redis connection test: {}", pong);
        
        Ok(RedisClient { manager })
    }
    
    /// Publish features to Redis channel
    pub async fn publish_features(
        &self,
        channel: &str,
        features: &serde_json::Value,
    ) -> Result<()> {
        let mut conn = self.manager.clone();
        let json_str = serde_json::to_string(features)?;
        conn.publish::<_, _, ()>(channel, json_str).await?;
        Ok(())
    }
    
    /// Get Redis connection manager
    pub fn connection_manager(&self) -> ConnectionManager {
        self.manager.clone()
    }
}
