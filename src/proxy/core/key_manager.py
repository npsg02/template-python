"""Key management for provider API keys."""

import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..models import ProviderKey, Provider, KeyStatus
from ..models.database import get_db_session
from ..core.encryption import decrypt_api_key, mask_api_key
from ..config import settings


class KeySelectionStrategy:
    """Key selection strategies for load balancing."""
    
    ROUND_ROBIN = "round_robin"
    PRIORITY = "priority"
    LEAST_USED = "least_used"
    WEIGHTED_RANDOM = "weighted_random"


class KeyManager:
    """Manages API key selection, health tracking, and usage monitoring."""
    
    def __init__(self):
        self.redis_client = None
        self._redis_url = settings.redis.url
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis client."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self._redis_url)
        return self.redis_client
    
    async def select_key(self, provider_id: int, strategy: str = KeySelectionStrategy.PRIORITY) -> Optional[ProviderKey]:
        """Select an available API key for a provider.
        
        Args:
            provider_id: Provider ID
            strategy: Key selection strategy
            
        Returns:
            Selected provider key or None if no keys available
        """
        with get_db_session() as db:
            # Get active keys for the provider
            keys = db.query(ProviderKey).filter(
                and_(
                    ProviderKey.provider_id == provider_id,
                    ProviderKey.status == KeyStatus.ACTIVE,
                    ProviderKey.consecutive_failures < 5  # Skip keys with too many failures
                )
            ).all()
            
            if not keys:
                return None
            
            # Filter out rate-limited or exhausted keys
            available_keys = []
            redis_client = await self._get_redis()
            
            for key in keys:
                if await self._is_key_available(key, redis_client):
                    available_keys.append(key)
            
            if not available_keys:
                return None
            
            # Apply selection strategy
            if strategy == KeySelectionStrategy.PRIORITY:
                selected_key = min(available_keys, key=lambda k: k.priority)
            elif strategy == KeySelectionStrategy.LEAST_USED:
                selected_key = min(available_keys, key=lambda k: k.current_daily_usage)
            elif strategy == KeySelectionStrategy.ROUND_ROBIN:
                selected_key = await self._round_robin_select(available_keys, redis_client)
            else:
                # Default to priority
                selected_key = min(available_keys, key=lambda k: k.priority)
            
            # Update last used timestamp
            selected_key.last_used_at = datetime.utcnow()
            db.commit()
            
            return selected_key
    
    async def _is_key_available(self, key: ProviderKey, redis_client: redis.Redis) -> bool:
        """Check if key is available (not rate limited)."""
        now = datetime.utcnow()
        
        # Check daily quota
        if key.daily_quota and key.current_daily_usage >= key.daily_quota:
            return False
        
        # Check monthly quota
        if key.monthly_quota and key.current_monthly_usage >= key.monthly_quota:
            return False
        
        # Check rate limits in Redis
        rpm_key = f"rate_limit:key:{key.id}:rpm"
        tpm_key = f"rate_limit:key:{key.id}:tpm"
        
        # Check requests per minute
        if key.rate_limit_rpm:
            current_rpm = await redis_client.get(rpm_key)
            if current_rpm and int(current_rpm) >= key.rate_limit_rpm:
                return False
        
        # Check tokens per minute  
        if key.rate_limit_tpm:
            current_tpm = await redis_client.get(tpm_key)
            if current_tpm and int(current_tpm) >= key.rate_limit_tpm:
                return False
        
        return True
    
    async def _round_robin_select(self, keys: List[ProviderKey], redis_client: redis.Redis) -> ProviderKey:
        """Select key using round-robin strategy."""
        provider_id = keys[0].provider_id
        rr_key = f"round_robin:provider:{provider_id}"
        
        # Get current index
        current_index = await redis_client.get(rr_key)
        if current_index is None:
            current_index = 0
        else:
            current_index = int(current_index)
        
        # Select key and update index
        selected_key = keys[current_index % len(keys)]
        next_index = (current_index + 1) % len(keys)
        await redis_client.set(rr_key, next_index, ex=3600)  # Expire after 1 hour
        
        return selected_key
    
    async def record_usage(self, key_id: int, tokens_used: int = 0, success: bool = True):
        """Record API key usage."""
        redis_client = await self._get_redis()
        
        with get_db_session() as db:
            key = db.query(ProviderKey).filter(ProviderKey.id == key_id).first()
            if not key:
                return
            
            # Update usage counters
            key.current_daily_usage += 1
            key.current_monthly_usage += 1
            
            if success:
                key.consecutive_failures = 0
                key.last_used_at = datetime.utcnow()
            else:
                key.consecutive_failures += 1
                key.last_failed_at = datetime.utcnow()
                
                # Disable key if too many consecutive failures
                if key.consecutive_failures >= 10:
                    key.status = KeyStatus.FAILED
            
            db.commit()
        
        # Update rate limiting counters in Redis
        now = int(time.time())
        minute_key = f"rate_limit:key:{key_id}:rpm"
        token_key = f"rate_limit:key:{key_id}:tpm"
        
        # Increment request counter
        await redis_client.incr(minute_key)
        await redis_client.expire(minute_key, 60)
        
        # Increment token counter
        if tokens_used > 0:
            await redis_client.incrby(token_key, tokens_used)
            await redis_client.expire(token_key, 60)
    
    async def mark_key_failed(self, key_id: int, error_type: str = "unknown"):
        """Mark a key as failed."""
        await self.record_usage(key_id, success=False)
        
        # Additional failure tracking in Redis
        redis_client = await self._get_redis()
        failure_key = f"key_failures:{key_id}"
        await redis_client.incr(failure_key)
        await redis_client.expire(failure_key, 3600)  # Track failures for 1 hour
    
    async def get_key_health(self, key_id: int) -> Dict[str, Any]:
        """Get health status of a key."""
        redis_client = await self._get_redis()
        
        with get_db_session() as db:
            key = db.query(ProviderKey).filter(ProviderKey.id == key_id).first()
            if not key:
                return {}
            
            # Get current rate limiting status
            rpm_key = f"rate_limit:key:{key_id}:rpm"
            tpm_key = f"rate_limit:key:{key_id}:tpm"
            failure_key = f"key_failures:{key_id}"
            
            current_rpm = await redis_client.get(rpm_key) or 0
            current_tpm = await redis_client.get(tpm_key) or 0
            recent_failures = await redis_client.get(failure_key) or 0
            
            return {
                "key_id": key.key_id,
                "status": key.status,
                "consecutive_failures": key.consecutive_failures,
                "current_daily_usage": key.current_daily_usage,
                "current_monthly_usage": key.current_monthly_usage,
                "daily_quota": key.daily_quota,
                "monthly_quota": key.monthly_quota,
                "current_rpm": int(current_rpm),
                "current_tpm": int(current_tpm),
                "rate_limit_rpm": key.rate_limit_rpm,
                "rate_limit_tpm": key.rate_limit_tpm,
                "recent_failures": int(recent_failures),
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "last_failed_at": key.last_failed_at.isoformat() if key.last_failed_at else None,
                "is_available": await self._is_key_available(key, redis_client)
            }
    
    async def reset_daily_usage(self):
        """Reset daily usage counters for all keys."""
        with get_db_session() as db:
            db.query(ProviderKey).update({ProviderKey.current_daily_usage: 0})
            db.commit()
    
    async def reset_monthly_usage(self):
        """Reset monthly usage counters for all keys."""
        with get_db_session() as db:
            db.query(ProviderKey).update({ProviderKey.current_monthly_usage: 0})
            db.commit()
    
    def get_decrypted_key(self, provider_key: ProviderKey) -> str:
        """Get decrypted API key value."""
        return decrypt_api_key(provider_key.key_value_encrypted)
    
    def get_masked_key(self, provider_key: ProviderKey) -> str:
        """Get masked API key for logging."""
        decrypted = self.get_decrypted_key(provider_key)
        return mask_api_key(decrypted)


# Global key manager instance
key_manager = KeyManager()