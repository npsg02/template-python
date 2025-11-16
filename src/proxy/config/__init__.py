"""Configuration for the OpenAI proxy."""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/openai_proxy",
        env="DATABASE_URL"
    )
    echo: bool = Field(default=False, env="DATABASE_ECHO")
    pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = Field(default=0, env="REDIS_DB")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    ssl: bool = Field(default=False, env="REDIS_SSL")
    socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(default=5, env="REDIS_CONNECT_TIMEOUT")


class S3Settings(BaseSettings):
    """S3 configuration settings."""
    
    endpoint_url: Optional[str] = Field(default=None, env="S3_ENDPOINT_URL")
    access_key: str = Field(default="", env="S3_ACCESS_KEY")
    secret_key: str = Field(default="", env="S3_SECRET_KEY")
    bucket_name: str = Field(default="openai-proxy", env="S3_BUCKET_NAME")
    region: str = Field(default="us-east-1", env="S3_REGION")
    use_ssl: bool = Field(default=True, env="S3_USE_SSL")


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    encryption_key: str = Field(
        default="your-encryption-key-32-chars!!",
        env="ENCRYPTION_KEY"
    )


class ProxySettings(BaseSettings):
    """Proxy-specific configuration settings."""
    
    default_timeout: int = Field(default=30, env="PROXY_DEFAULT_TIMEOUT")
    max_retries: int = Field(default=3, env="PROXY_MAX_RETRIES")
    enable_streaming: bool = Field(default=True, env="PROXY_ENABLE_STREAMING")
    enable_content_logging: bool = Field(
        default=False, env="PROXY_ENABLE_CONTENT_LOGGING"
    )
    content_retention_days: int = Field(
        default=30, env="PROXY_CONTENT_RETENTION_DAYS"
    )
    max_fallback_attempts: int = Field(
        default=3, env="PROXY_MAX_FALLBACK_ATTEMPTS"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5, env="PROXY_CIRCUIT_BREAKER_FAILURE_THRESHOLD"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60, env="PROXY_CIRCUIT_BREAKER_RECOVERY_TIMEOUT"
    )


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration settings."""
    
    global_rpm: int = Field(default=1000, env="RATE_LIMIT_GLOBAL_RPM")
    global_tpm: int = Field(default=100000, env="RATE_LIMIT_GLOBAL_TPM")
    per_key_rpm: int = Field(default=100, env="RATE_LIMIT_PER_KEY_RPM")
    per_key_tpm: int = Field(default=10000, env="RATE_LIMIT_PER_KEY_TPM")
    per_ip_rpm: int = Field(default=60, env="RATE_LIMIT_PER_IP_RPM")
    window_size_minutes: int = Field(default=1, env="RATE_LIMIT_WINDOW_SIZE_MINUTES")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings."""
    
    enable_metrics: bool = Field(default=True, env="MONITORING_ENABLE_METRICS")
    metrics_port: int = Field(default=8001, env="MONITORING_METRICS_PORT")
    enable_tracing: bool = Field(default=False, env="MONITORING_ENABLE_TRACING")
    tracing_endpoint: Optional[str] = Field(
        default=None, env="MONITORING_TRACING_ENDPOINT"
    )
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")


class AppSettings(BaseSettings):
    """Main application settings."""
    
    name: str = Field(default="OpenAI Proxy", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    description: str = Field(
        default="OpenAI-compatible proxy with multi-provider support",
        env="APP_DESCRIPTION"
    )
    host: str = Field(default="0.0.0.0", env="APP_HOST")
    port: int = Field(default=8000, env="APP_PORT")
    debug: bool = Field(default=False, env="APP_DEBUG")
    reload: bool = Field(default=False, env="APP_RELOAD")
    workers: int = Field(default=1, env="APP_WORKERS")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["*"], env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(
        default=True, env="CORS_ALLOW_CREDENTIALS"
    )
    cors_allow_methods: List[str] = Field(
        default=["*"], env="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"], env="CORS_ALLOW_HEADERS"
    )


class Settings(BaseSettings):
    """Combined application settings."""
    
    app: AppSettings = AppSettings()
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    s3: S3Settings = S3Settings()
    security: SecuritySettings = SecuritySettings()
    proxy: ProxySettings = ProxySettings()
    rate_limit: RateLimitSettings = RateLimitSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()