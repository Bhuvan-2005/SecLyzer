use crate::config::Config;
use anyhow::Result;
use reqwest::Client as HttpClient;
use serde_json::json;
use std::collections::HashMap;

pub struct InfluxClient {
    client: HttpClient,
    url: String,
    token: String,
    org: String,
    bucket: String,
}

impl InfluxClient {
    pub async fn new(config: &Config) -> Result<Self> {
        let client = HttpClient::new();
        
        // Test connection
        let response = client
            .get(&format!("{}/api/v2/ready", config.influx_url))
            .send()
            .await?;
        
        if response.status().is_success() {
            tracing::info!("InfluxDB connection successful");
        } else {
            tracing::warn!("InfluxDB status: {}", response.status());
        }
        
        Ok(InfluxClient {
            client,
            url: config.influx_url.clone(),
            token: config.influx_token.clone(),
            org: config.influx_org.clone(),
            bucket: config.influx_bucket.clone(),
        })
    }
    
    /// Write a point in line protocol format
    pub async fn write_line_protocol(&self, line_protocol: String) -> Result<()> {
        let response = self
            .client
            .post(&format!(
                "{}/api/v2/write?org={}&bucket={}",
                self.url, self.org, self.bucket
            ))
            .header("Authorization", format!("Token {}", self.token))
            .header("Content-Type", "text/plain")
            .body(line_protocol)
            .send()
            .await?;
        
        if response.status().is_success() {
            Ok(())
        } else {
            let text = response.text().await.unwrap_or_default();
            anyhow::bail!("InfluxDB write failed: {}", text)
        }
    }
    
    /// Convert tags and fields to line protocol
    pub fn build_line_protocol(
        measurement: &str,
        tags: &HashMap<String, String>,
        fields: &HashMap<String, f64>,
        timestamp_ns: i64,
    ) -> String {
        let mut line = measurement.to_string();
        
        // Add tags
        for (k, v) in tags {
            line.push(',');
            line.push_str(&format!("{}={}", k, v));
        }
        
        // Add fields
        line.push(' ');
        let field_strs: Vec<String> = fields
            .iter()
            .map(|(k, v)| format!("{}={}", k, v))
            .collect();
        line.push_str(&field_strs.join(","));
        
        // Add timestamp
        line.push(' ');
        line.push_str(&timestamp_ns.to_string());
        
        line
    }
}
