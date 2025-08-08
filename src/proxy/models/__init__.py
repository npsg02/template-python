"""Database models for the OpenAI proxy."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import json

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey,
    Index, UniqueConstraint, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ProviderStatus(str, Enum):
    """Provider status enumeration."""
    ACTIVE = "active"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"


class KeyStatus(str, Enum):
    """API key status enumeration."""
    ACTIVE = "active"
    DISABLED = "disabled"
    EXHAUSTED = "exhausted"
    FAILED = "failed"


class Provider(Base):
    """Provider model for storing LLM provider configurations."""
    
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    provider_type = Column(String(50), nullable=False)  # openai, anthropic, ollama, custom
    base_url = Column(String(500), nullable=False)
    config_json = Column(JSON, default=dict)  # Additional provider-specific config
    status = Column(String(20), default=ProviderStatus.ACTIVE, nullable=False)
    timeout_seconds = Column(Integer, default=30)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    provider_keys = relationship("ProviderKey", back_populates="provider", cascade="all, delete-orphan")
    model_mappings = relationship("ModelMapping", back_populates="provider", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Provider(name='{self.name}', type='{self.provider_type}', status='{self.status}')>"


class ProviderKey(Base):
    """API keys for providers with metadata."""
    
    __tablename__ = "provider_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    key_id = Column(String(100), nullable=False, index=True)  # Identifier for the key
    key_value_encrypted = Column(Text, nullable=False)  # Encrypted API key
    priority = Column(Integer, default=100)  # Lower = higher priority
    status = Column(String(20), default=KeyStatus.ACTIVE, nullable=False)
    rate_limit_rpm = Column(Integer, default=1000)  # Requests per minute
    rate_limit_tpm = Column(Integer, default=100000)  # Tokens per minute
    daily_quota = Column(Integer)  # Daily request quota
    monthly_quota = Column(Integer)  # Monthly request quota
    current_daily_usage = Column(Integer, default=0)
    current_monthly_usage = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    last_failed_at = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    provider = relationship("Provider", back_populates="provider_keys")
    
    # Indexes
    __table_args__ = (
        Index('idx_provider_key_status', 'provider_id', 'status'),
        Index('idx_provider_key_priority', 'provider_id', 'priority'),
        UniqueConstraint('provider_id', 'key_id', name='uq_provider_key_id'),
    )
    
    def __repr__(self):
        return f"<ProviderKey(key_id='{self.key_id}', provider_id={self.provider_id}, status='{self.status}')>"


class ModelMapping(Base):
    """Model name mappings from client to provider models."""
    
    __tablename__ = "model_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    alias_name = Column(String(200), nullable=False, index=True)  # Client-facing model name
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    provider_model_name = Column(String(200), nullable=False)  # Provider's model name
    order_index = Column(Integer, default=0)  # Order for fallback
    is_default = Column(Boolean, default=False)
    config_json = Column(JSON, default=dict)  # Model-specific config (temperature, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    provider = relationship("Provider", back_populates="model_mappings")
    
    # Indexes
    __table_args__ = (
        Index('idx_alias_name', 'alias_name'),
        Index('idx_alias_order', 'alias_name', 'order_index'),
    )
    
    def __repr__(self):
        return f"<ModelMapping(alias='{self.alias_name}', provider_model='{self.provider_model_name}')>"


class RequestAudit(Base):
    """Audit log for all proxy requests."""
    
    __tablename__ = "requests_audit"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), unique=True, nullable=False, index=True)
    tenant_id = Column(String(100), index=True)  # Optional tenant identifier
    client_ip = Column(String(45))  # IPv4/IPv6 address
    user_agent = Column(String(500))
    
    # Request details
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    model_alias = Column(String(200))
    provider_id = Column(Integer, ForeignKey("providers.id"))
    provider_model_name = Column(String(200))
    key_id = Column(String(100))
    
    # Response details
    status_code = Column(Integer)
    latency_ms = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    
    # Fallback tracking
    fallback_chain_json = Column(JSON)  # Array of attempted providers/keys
    fallback_count = Column(Integer, default=0)
    
    # Error tracking
    error_type = Column(String(100))
    error_message = Column(Text)
    
    # Optional content storage
    s3_request_key = Column(String(500))  # S3 key for request content
    s3_response_key = Column(String(500))  # S3 key for response content
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_request_audit_created', 'created_at'),
        Index('idx_request_audit_provider', 'provider_id', 'created_at'),
        Index('idx_request_audit_tenant', 'tenant_id', 'created_at'),
        Index('idx_request_audit_model', 'model_alias', 'created_at'),
    )
    
    def __repr__(self):
        return f"<RequestAudit(request_id='{self.request_id}', status={self.status_code}, latency={self.latency_ms}ms)>"


class FallbackPolicy(Base):
    """Configurable fallback policies."""
    
    __tablename__ = "fallback_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    policy_json = Column(JSON, nullable=False)  # Detailed policy configuration
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<FallbackPolicy(name='{self.name}', is_default={self.is_default})>"


class User(Base):
    """Users for admin access."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    hashed_password = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    api_key = Column(String(200), unique=True, index=True)  # For API access
    rate_limit_rpm = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<User(username='{self.username}', is_admin={self.is_admin})>"


class RateLimitLog(Base):
    """Rate limiting tracking."""
    
    __tablename__ = "rate_limit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(200), nullable=False, index=True)  # API key, IP, user ID
    identifier_type = Column(String(50), nullable=False)  # 'api_key', 'ip', 'user'
    endpoint = Column(String(200))
    requests_count = Column(Integer, default=1)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_duration_seconds = Column(Integer, default=60)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_rate_limit_identifier', 'identifier', 'window_start'),
        Index('idx_rate_limit_window', 'window_start'),
    )
    
    def __repr__(self):
        return f"<RateLimitLog(identifier='{self.identifier}', count={self.requests_count})>"