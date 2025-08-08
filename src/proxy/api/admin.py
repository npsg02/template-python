"""Admin API endpoints for managing providers, keys, and mappings."""

import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..models import Provider, ProviderKey, ModelMapping, User, ProviderStatus, KeyStatus
from ..models.database import get_db
from ..core.encryption import encrypt_api_key, mask_api_key
from ..core.key_manager import key_manager
from ..core.model_mapper import model_mapper
from ..core.fallback import fallback_engine


router = APIRouter(prefix="/admin", tags=["Admin API"])


# Request/Response Models
class ProviderCreate(BaseModel):
    name: str = Field(..., description="Provider name")
    provider_type: str = Field(..., description="Provider type (openai, anthropic, etc.)")
    base_url: str = Field(..., description="Base URL for the provider")
    config_json: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Provider configuration")
    timeout_seconds: Optional[int] = Field(30, description="Request timeout in seconds")
    max_retries: Optional[int] = Field(3, description="Maximum retries")


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None


class ProviderResponse(BaseModel):
    id: int
    name: str
    provider_type: str
    base_url: str
    config_json: Dict[str, Any]
    status: str
    timeout_seconds: int
    max_retries: int
    created_at: str
    updated_at: Optional[str]


class KeyCreate(BaseModel):
    provider_id: int = Field(..., description="Provider ID")
    key_id: str = Field(..., description="Key identifier")
    key_value: str = Field(..., description="API key value")
    priority: Optional[int] = Field(100, description="Key priority (lower = higher priority)")
    rate_limit_rpm: Optional[int] = Field(1000, description="Requests per minute limit")
    rate_limit_tpm: Optional[int] = Field(100000, description="Tokens per minute limit")
    daily_quota: Optional[int] = Field(None, description="Daily request quota")
    monthly_quota: Optional[int] = Field(None, description="Monthly request quota")


class KeyUpdate(BaseModel):
    key_id: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    rate_limit_rpm: Optional[int] = None
    rate_limit_tpm: Optional[int] = None
    daily_quota: Optional[int] = None
    monthly_quota: Optional[int] = None


class KeyResponse(BaseModel):
    id: int
    provider_id: int
    key_id: str
    masked_key: str
    priority: int
    status: str
    rate_limit_rpm: int
    rate_limit_tpm: int
    daily_quota: Optional[int]
    monthly_quota: Optional[int]
    current_daily_usage: int
    current_monthly_usage: int
    consecutive_failures: int
    created_at: str
    last_used_at: Optional[str]
    last_failed_at: Optional[str]


class MappingCreate(BaseModel):
    alias_name: str = Field(..., description="Client-facing model name")
    provider_id: int = Field(..., description="Provider ID")
    provider_model_name: str = Field(..., description="Provider's model name")
    order_index: Optional[int] = Field(0, description="Order for fallback")
    is_default: Optional[bool] = Field(False, description="Whether this is the default mapping")
    config_json: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Model-specific config")


class MappingUpdate(BaseModel):
    provider_model_name: Optional[str] = None
    order_index: Optional[int] = None
    is_default: Optional[bool] = None
    config_json: Optional[Dict[str, Any]] = None


class MappingResponse(BaseModel):
    id: int
    alias_name: str
    provider_id: int
    provider_model_name: str
    order_index: int
    is_default: bool
    config_json: Dict[str, Any]
    created_at: str
    updated_at: Optional[str]


# Provider Management
@router.post("/providers", response_model=ProviderResponse)
async def create_provider(provider_data: ProviderCreate, db: Session = Depends(get_db)):
    """Create a new provider."""
    # Check if provider name already exists
    existing = db.query(Provider).filter(Provider.name == provider_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider with name '{provider_data.name}' already exists"
        )
    
    provider = Provider(
        name=provider_data.name,
        provider_type=provider_data.provider_type,
        base_url=provider_data.base_url,
        config_json=provider_data.config_json,
        timeout_seconds=provider_data.timeout_seconds,
        max_retries=provider_data.max_retries,
        status=ProviderStatus.ACTIVE
    )
    
    db.add(provider)
    db.commit()
    db.refresh(provider)
    
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        config_json=provider.config_json,
        status=provider.status,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat() if provider.updated_at else None
    )


@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers(db: Session = Depends(get_db)):
    """List all providers."""
    providers = db.query(Provider).all()
    
    return [
        ProviderResponse(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            base_url=provider.base_url,
            config_json=provider.config_json,
            status=provider.status,
            timeout_seconds=provider.timeout_seconds,
            max_retries=provider.max_retries,
            created_at=provider.created_at.isoformat(),
            updated_at=provider.updated_at.isoformat() if provider.updated_at else None
        )
        for provider in providers
    ]


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """Get a specific provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        config_json=provider.config_json,
        status=provider.status,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat() if provider.updated_at else None
    )


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: int, 
    provider_data: ProviderUpdate, 
    db: Session = Depends(get_db)
):
    """Update a provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Update fields
    for field, value in provider_data.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    
    db.commit()
    db.refresh(provider)
    
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        config_json=provider.config_json,
        status=provider.status,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat() if provider.updated_at else None
    )


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    """Delete a provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    db.delete(provider)
    db.commit()
    
    return {"message": "Provider deleted successfully"}


# Key Management
@router.post("/keys", response_model=KeyResponse)
async def create_key(key_data: KeyCreate, db: Session = Depends(get_db)):
    """Create a new API key."""
    # Check if provider exists
    provider = db.query(Provider).filter(Provider.id == key_data.provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Check if key_id already exists for this provider
    existing = db.query(ProviderKey).filter(
        ProviderKey.provider_id == key_data.provider_id,
        ProviderKey.key_id == key_data.key_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Key with ID '{key_data.key_id}' already exists for this provider"
        )
    
    # Encrypt the API key
    encrypted_key = encrypt_api_key(key_data.key_value)
    
    provider_key = ProviderKey(
        provider_id=key_data.provider_id,
        key_id=key_data.key_id,
        key_value_encrypted=encrypted_key,
        priority=key_data.priority,
        rate_limit_rpm=key_data.rate_limit_rpm,
        rate_limit_tpm=key_data.rate_limit_tpm,
        daily_quota=key_data.daily_quota,
        monthly_quota=key_data.monthly_quota,
        status=KeyStatus.ACTIVE
    )
    
    db.add(provider_key)
    db.commit()
    db.refresh(provider_key)
    
    # Get masked key for response
    masked_key = mask_api_key(key_data.key_value)
    
    return KeyResponse(
        id=provider_key.id,
        provider_id=provider_key.provider_id,
        key_id=provider_key.key_id,
        masked_key=masked_key,
        priority=provider_key.priority,
        status=provider_key.status,
        rate_limit_rpm=provider_key.rate_limit_rpm,
        rate_limit_tpm=provider_key.rate_limit_tpm,
        daily_quota=provider_key.daily_quota,
        monthly_quota=provider_key.monthly_quota,
        current_daily_usage=provider_key.current_daily_usage,
        current_monthly_usage=provider_key.current_monthly_usage,
        consecutive_failures=provider_key.consecutive_failures,
        created_at=provider_key.created_at.isoformat(),
        last_used_at=provider_key.last_used_at.isoformat() if provider_key.last_used_at else None,
        last_failed_at=provider_key.last_failed_at.isoformat() if provider_key.last_failed_at else None
    )


@router.get("/keys", response_model=List[KeyResponse])
async def list_keys(provider_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List API keys."""
    query = db.query(ProviderKey)
    if provider_id:
        query = query.filter(ProviderKey.provider_id == provider_id)
    
    keys = query.all()
    
    result = []
    for key in keys:
        masked_key = key_manager.get_masked_key(key)
        result.append(KeyResponse(
            id=key.id,
            provider_id=key.provider_id,
            key_id=key.key_id,
            masked_key=masked_key,
            priority=key.priority,
            status=key.status,
            rate_limit_rpm=key.rate_limit_rpm,
            rate_limit_tpm=key.rate_limit_tpm,
            daily_quota=key.daily_quota,
            monthly_quota=key.monthly_quota,
            current_daily_usage=key.current_daily_usage,
            current_monthly_usage=key.current_monthly_usage,
            consecutive_failures=key.consecutive_failures,
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
            last_failed_at=key.last_failed_at.isoformat() if key.last_failed_at else None
        ))
    
    return result


@router.get("/keys/{key_id}/health")
async def get_key_health(key_id: int):
    """Get key health status."""
    health = await key_manager.get_key_health(key_id)
    if not health:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found"
        )
    return health


# Model Mapping Management
@router.post("/mappings", response_model=MappingResponse)
async def create_mapping(mapping_data: MappingCreate, db: Session = Depends(get_db)):
    """Create a new model mapping."""
    # Validate the mapping
    validation = model_mapper.validate_mapping(
        mapping_data.alias_name,
        mapping_data.provider_id,
        mapping_data.provider_model_name
    )
    
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation["error"]
        )
    
    mapping = model_mapper.create_mapping(
        alias_name=mapping_data.alias_name,
        provider_id=mapping_data.provider_id,
        provider_model_name=mapping_data.provider_model_name,
        order_index=mapping_data.order_index,
        is_default=mapping_data.is_default,
        config=mapping_data.config_json
    )
    
    return MappingResponse(
        id=mapping.id,
        alias_name=mapping.alias_name,
        provider_id=mapping.provider_id,
        provider_model_name=mapping.provider_model_name,
        order_index=mapping.order_index,
        is_default=mapping.is_default,
        config_json=mapping.config_json,
        created_at=mapping.created_at.isoformat(),
        updated_at=mapping.updated_at.isoformat() if mapping.updated_at else None
    )


@router.get("/mappings", response_model=List[MappingResponse])
async def list_mappings(
    alias_name: Optional[str] = None,
    provider_id: Optional[int] = None
):
    """List model mappings."""
    mappings = model_mapper.list_mappings(alias_name=alias_name, provider_id=provider_id)
    
    return [
        MappingResponse(
            id=mapping.id,
            alias_name=mapping.alias_name,
            provider_id=mapping.provider_id,
            provider_model_name=mapping.provider_model_name,
            order_index=mapping.order_index,
            is_default=mapping.is_default,
            config_json=mapping.config_json,
            created_at=mapping.created_at.isoformat(),
            updated_at=mapping.updated_at.isoformat() if mapping.updated_at else None
        )
        for mapping in mappings
    ]


@router.get("/health")
async def get_system_health():
    """Get overall system health."""
    # Get provider health from fallback engine
    # This would include circuit breaker states, key health, etc.
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


@router.post("/circuit-breaker/{provider_id}/reset")
async def reset_circuit_breaker(provider_id: int):
    """Reset circuit breaker for a provider."""
    await fallback_engine.reset_circuit_breaker(provider_id)
    return {"message": f"Circuit breaker reset for provider {provider_id}"}