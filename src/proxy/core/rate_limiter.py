"""Rate limiting functionality using Redis."""

import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from dataclasses import dataclass

from ..config import settings


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None


class RateLimiter:
    """Redis-based rate limiter with sliding window implementation."""
    
    def __init__(self):
        self.redis_client = None
        self._redis_url = settings.redis.url
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis client."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self._redis_url)
        return self.redis_client
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        identifier_type: str = "api_key"
    ) -> RateLimitResult:
        """Check if identifier is within rate limits.
        
        Args:
            identifier: Unique identifier (API key, IP, user ID)
            limit: Maximum requests in window
            window_seconds: Time window in seconds
            identifier_type: Type of identifier for logging
            
        Returns:
            RateLimitResult with status and metadata
        """
        redis_client = await self._get_redis()
        
        now = time.time()
        key = f"rate_limit:{identifier_type}:{identifier}"
        
        # Use sliding window with Redis sorted sets
        async with redis_client.pipeline() as pipe:
            # Remove old entries
            await pipe.zremrangebyscore(key, 0, now - window_seconds)
            
            # Count current requests in window
            await pipe.zcard(key)
            
            # Add current request
            await pipe.zadd(key, {str(now): now})
            
            # Set expiration
            await pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
        
        current_count = results[1]
        
        if current_count >= limit:
            # Rate limit exceeded
            oldest_request_time = await redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_request_time:
                reset_time = oldest_request_time[0][1] + window_seconds
                retry_after = max(1, int(reset_time - now))
            else:
                reset_time = now + window_seconds
                retry_after = window_seconds
            
            # Remove the request we just added since it's rejected
            await redis_client.zrem(key, str(now))
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                retry_after=retry_after
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=limit - current_count - 1,
            reset_time=now + window_seconds
        )
    
    async def check_multiple_limits(
        self,
        checks: List[Dict[str, Any]]
    ) -> Dict[str, RateLimitResult]:
        """Check multiple rate limits at once.
        
        Args:
            checks: List of dicts with keys: identifier, limit, window_seconds, identifier_type
            
        Returns:
            Dict mapping check names to RateLimitResult
        """
        results = {}
        
        for i, check in enumerate(checks):
            check_name = check.get("name", f"check_{i}")
            result = await self.check_rate_limit(
                check["identifier"],
                check["limit"],
                check["window_seconds"],
                check.get("identifier_type", "api_key")
            )
            results[check_name] = result
        
        return results
    
    async def get_usage_stats(
        self,
        identifier: str,
        window_seconds: int,
        identifier_type: str = "api_key"
    ) -> Dict[str, Any]:
        """Get usage statistics for an identifier.
        
        Args:
            identifier: Unique identifier
            window_seconds: Time window in seconds
            identifier_type: Type of identifier
            
        Returns:
            Usage statistics
        """
        redis_client = await self._get_redis()
        
        now = time.time()
        key = f"rate_limit:{identifier_type}:{identifier}"
        
        # Clean old entries
        await redis_client.zremrangebyscore(key, 0, now - window_seconds)
        
        # Get all requests in current window
        requests = await redis_client.zrange(key, 0, -1, withscores=True)
        
        if not requests:
            return {
                "total_requests": 0,
                "requests_per_minute": 0,
                "window_start": now - window_seconds,
                "window_end": now,
                "oldest_request": None,
                "newest_request": None
            }
        
        oldest_time = requests[0][1]
        newest_time = requests[-1][1]
        total_requests = len(requests)
        
        # Calculate requests per minute
        actual_window = min(window_seconds, now - oldest_time)
        requests_per_minute = (total_requests / actual_window) * 60 if actual_window > 0 else 0
        
        return {
            "total_requests": total_requests,
            "requests_per_minute": requests_per_minute,
            "window_start": now - window_seconds,
            "window_end": now,
            "oldest_request": oldest_time,
            "newest_request": newest_time,
            "window_utilization": actual_window / window_seconds
        }
    
    async def reset_limits(self, identifier: str, identifier_type: str = "api_key"):
        """Reset rate limits for an identifier.
        
        Args:
            identifier: Unique identifier
            identifier_type: Type of identifier
        """
        redis_client = await self._get_redis()
        
        key = f"rate_limit:{identifier_type}:{identifier}"
        await redis_client.delete(key)


class GlobalRateLimiter:
    """Global rate limiter that applies limits based on configuration."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.global_rpm = settings.rate_limit.global_rpm
        self.global_tpm = settings.rate_limit.global_tpm
        self.per_key_rpm = settings.rate_limit.per_key_rpm
        self.per_key_tpm = settings.rate_limit.per_key_tpm
        self.per_ip_rpm = settings.rate_limit.per_ip_rpm
        self.window_size = settings.rate_limit.window_size_minutes * 60
    
    async def check_request_limits(
        self,
        api_key: Optional[str] = None,
        ip_address: Optional[str] = None,
        estimated_tokens: int = 0
    ) -> Dict[str, RateLimitResult]:
        """Check all applicable rate limits for a request.
        
        Args:
            api_key: API key of the request
            ip_address: IP address of the request
            estimated_tokens: Estimated token usage
            
        Returns:
            Dict of rate limit results
        """
        checks = []
        
        # Global request limit
        checks.append({
            "name": "global_rpm",
            "identifier": "global",
            "limit": self.global_rpm,
            "window_seconds": self.window_size,
            "identifier_type": "global"
        })
        
        # Global token limit
        if estimated_tokens > 0:
            checks.append({
                "name": "global_tpm",
                "identifier": "global_tokens",
                "limit": self.global_tpm,
                "window_seconds": self.window_size,
                "identifier_type": "global"
            })
        
        # Per-key limits
        if api_key:
            checks.append({
                "name": "key_rpm",
                "identifier": api_key,
                "limit": self.per_key_rpm,
                "window_seconds": self.window_size,
                "identifier_type": "api_key"
            })
            
            if estimated_tokens > 0:
                checks.append({
                    "name": "key_tpm",
                    "identifier": f"{api_key}_tokens",
                    "limit": self.per_key_tpm,
                    "window_seconds": self.window_size,
                    "identifier_type": "api_key"
                })
        
        # Per-IP limits
        if ip_address:
            checks.append({
                "name": "ip_rpm",
                "identifier": ip_address,
                "limit": self.per_ip_rpm,
                "window_seconds": self.window_size,
                "identifier_type": "ip"
            })
        
        return await self.rate_limiter.check_multiple_limits(checks)
    
    async def record_token_usage(self, api_key: str, tokens_used: int):
        """Record actual token usage after request completion.
        
        Args:
            api_key: API key used
            tokens_used: Actual tokens consumed
        """
        # For token rate limiting, we use a separate tracking mechanism
        # This helps with accurate token-based rate limiting
        redis_client = await self.rate_limiter._get_redis()
        
        now = time.time()
        key = f"rate_limit:api_key:{api_key}_tokens"
        
        # Add actual token usage
        await redis_client.zadd(key, {f"{now}_{tokens_used}": now})
        await redis_client.expire(key, self.window_size)
        
        # Clean old entries and sum tokens in current window
        await redis_client.zremrangebyscore(key, 0, now - self.window_size)


# Global rate limiter instance
global_rate_limiter = GlobalRateLimiter()