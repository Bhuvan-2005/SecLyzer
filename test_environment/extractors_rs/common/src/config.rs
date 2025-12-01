use anyhow::Result;
use std::env;

#[derive(Clone, Debug)]
pub struct Config {
    pub redis_host: String,
    pub redis_port: u16,
    pub redis_password: Option<String>,
    
    pub influx_url: String,
    pub influx_token: String,
    pub influx_org: String,
    pub influx_bucket: String,
    
    pub window_seconds: u64,
    pub update_interval: u64,
    
    pub dev_mode: bool,
}

impl Config {
    pub fn from_env() -> Result<Self> {
        dotenv::dotenv().ok();
        
        Ok(Config {
            redis_host: env::var("REDIS_HOST").unwrap_or_else(|_| "localhost".to_string()),
            redis_port: env::var("REDIS_PORT")
                .unwrap_or_else(|_| "6379".to_string())
                .parse()?,
            redis_password: env::var("REDIS_PASSWORD").ok(),
            
            influx_url: env::var("INFLUX_URL")
                .unwrap_or_else(|_| "http://localhost:8086".to_string()),
            influx_token: env::var("INFLUX_TOKEN")
                .unwrap_or_else(|_| "token".to_string()),
            influx_org: env::var("INFLUX_ORG")
                .unwrap_or_else(|_| "seclyzer".to_string()),
            influx_bucket: env::var("INFLUX_BUCKET")
                .unwrap_or_else(|_| "behavioral_data".to_string()),
            
            window_seconds: env::var("WINDOW_SECONDS")
                .unwrap_or_else(|_| "30".to_string())
                .parse()?,
            update_interval: env::var("UPDATE_INTERVAL")
                .unwrap_or_else(|_| "5".to_string())
                .parse()?,
            
            dev_mode: env::var("SECLYZER_DEV_MODE")
                .unwrap_or_else(|_| "false".to_string())
                .parse()?,
        })
    }
}
