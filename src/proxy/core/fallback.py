"""Fallback engine with circuit breaker pattern."""

import asyncio
import json
import time
from typing import Optional, List, Dict, Any, Union, AsyncIterator, Callable
from dataclasses import dataclass
from enum import Enum
import redis.asyncio as redis

from ..providers.base import (
    BaseProvider, ProviderRequest, ProviderResponse, StreamChunk,
    ProviderError, RateLimitError, AuthenticationError, QuotaExceededError
)
from ..models import Provider
from ..core.key_manager import key_manager, KeyManager
from ..core.model_mapper import model_mapper
from ..config import settings


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class FallbackAttempt:
    """Record of a fallback attempt."""
    provider_id: int
    provider_name: str
    key_id: Optional[str]
    error_type: Optional[str]
    error_message: Optional[str]
    status_code: Optional[int]
    latency_ms: Optional[int]
    success: bool


@dataclass
class FallbackResult:
    """Result of fallback execution."""
    success: bool
    response: Optional[Union[ProviderResponse, AsyncIterator[StreamChunk]]]
    attempts: List[FallbackAttempt]
    total_latency_ms: int
    final_provider_id: Optional[int]
    final_key_id: Optional[str]


class CircuitBreaker:
    """Circuit breaker for provider health monitoring."""
    
    def __init__(self, provider_id: int, redis_client: redis.Redis):
        self.provider_id = provider_id
        self.redis_client = redis_client
        self.failure_threshold = settings.proxy.circuit_breaker_failure_threshold
        self.recovery_timeout = settings.proxy.circuit_breaker_recovery_timeout
    
    async def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        state_key = f"circuit_breaker:{self.provider_id}:state"
        state = await self.redis_client.get(state_key)
        
        if state is None:
            return CircuitBreakerState.CLOSED
        
        return CircuitBreakerState(state.decode())
    
    async def record_success(self):
        """Record a successful request."""
        state_key = f"circuit_breaker:{self.provider_id}:state"
        failure_key = f"circuit_breaker:{self.provider_id}:failures"
        
        # Reset failure count and close circuit
        await self.redis_client.delete(failure_key)
        await self.redis_client.set(state_key, CircuitBreakerState.CLOSED.value)
    
    async def record_failure(self):
        """Record a failed request."""
        failure_key = f"circuit_breaker:{self.provider_id}:failures"
        state_key = f"circuit_breaker:{self.provider_id}:state"
        
        # Increment failure count
        failures = await self.redis_client.incr(failure_key)
        await self.redis_client.expire(failure_key, self.recovery_timeout)
        
        # Check if we should open the circuit
        if failures >= self.failure_threshold:
            await self.redis_client.set(state_key, CircuitBreakerState.OPEN.value, ex=self.recovery_timeout)
    
    async def can_execute(self) -> bool:
        """Check if requests can be executed."""
        state = await self.get_state()
        
        if state == CircuitBreakerState.CLOSED:
            return True
        elif state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            state_key = f"circuit_breaker:{self.provider_id}:state"
            ttl = await self.redis_client.ttl(state_key)
            
            if ttl <= 0:  # Timeout expired, try half-open
                await self.redis_client.set(state_key, CircuitBreakerState.HALF_OPEN.value)
                return True
            return False
        elif state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False


class FallbackEngine:
    """Manages fallback logic across providers and keys."""
    
    def __init__(self):
        self.redis_client = None
        self._redis_url = settings.redis.url
        self.max_fallback_attempts = settings.proxy.max_fallback_attempts
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis client."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self._redis_url)
        return self.redis_client
    
    async def execute_with_fallback(
        self,
        model_alias: str,
        request: ProviderRequest,
        provider_factory: Callable[[Provider, str], BaseProvider],
        tenant_id: Optional[str] = None
    ) -> FallbackResult:
        """Execute request with fallback across providers and keys.
        
        Args:
            model_alias: Client model name
            request: Provider request
            provider_factory: Function to create provider instances
            tenant_id: Optional tenant ID
            
        Returns:
            FallbackResult with execution details
        """
        start_time = time.time()
        attempts = []
        redis_client = await self._get_redis()
        
        # Get provider mappings for the model
        mappings = model_mapper.get_provider_mapping(model_alias, tenant_id)
        
        if not mappings:
            return FallbackResult(
                success=False,
                response=None,
                attempts=[],
                total_latency_ms=0,
                final_provider_id=None,
                final_key_id=None
            )
        
        attempt_count = 0
        
        for provider, provider_model_name, config in mappings:
            if attempt_count >= self.max_fallback_attempts:
                break
            
            # Check circuit breaker
            circuit_breaker = CircuitBreaker(provider.id, redis_client)
            if not await circuit_breaker.can_execute():
                attempts.append(FallbackAttempt(
                    provider_id=provider.id,
                    provider_name=provider.name,
                    key_id=None,
                    error_type="circuit_breaker_open",
                    error_message="Circuit breaker is open",
                    status_code=None,
                    latency_ms=0,
                    success=False
                ))
                continue
            
            # Try multiple keys for this provider
            key_attempts = 0
            max_key_attempts = 3
            
            while key_attempts < max_key_attempts and attempt_count < self.max_fallback_attempts:
                provider_key = await key_manager.select_key(provider.id)
                
                if not provider_key:
                    attempts.append(FallbackAttempt(
                        provider_id=provider.id,
                        provider_name=provider.name,
                        key_id=None,
                        error_type="no_available_keys",
                        error_message="No available API keys",
                        status_code=None,
                        latency_ms=0,
                        success=False
                    ))
                    break
                
                try:
                    # Create provider instance with decrypted key
                    api_key = key_manager.get_decrypted_key(provider_key)
                    provider_instance = provider_factory(provider, api_key)
                    
                    # Update request with provider model name
                    provider_request = ProviderRequest(
                        model=provider_model_name,
                        messages=request.messages,
                        prompt=request.prompt,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        top_p=request.top_p,
                        frequency_penalty=request.frequency_penalty,
                        presence_penalty=request.presence_penalty,
                        stop=request.stop,
                        stream=request.stream,
                        user=request.user,
                        extra_params={**(request.extra_params or {}), **config}
                    )
                    
                    # Execute request
                    attempt_start = time.time()
                    
                    if hasattr(request, 'messages') and request.messages:
                        response = await provider_instance.chat_completion(provider_request)
                    else:
                        response = await provider_instance.completion(provider_request)
                    
                    attempt_latency = int((time.time() - attempt_start) * 1000)
                    
                    # Record success
                    await key_manager.record_usage(provider_key.id, success=True)
                    await circuit_breaker.record_success()
                    
                    attempts.append(FallbackAttempt(
                        provider_id=provider.id,
                        provider_name=provider.name,
                        key_id=provider_key.key_id,
                        error_type=None,
                        error_message=None,
                        status_code=200,
                        latency_ms=attempt_latency,
                        success=True
                    ))
                    
                    total_latency = int((time.time() - start_time) * 1000)
                    
                    return FallbackResult(
                        success=True,
                        response=response,
                        attempts=attempts,
                        total_latency_ms=total_latency,
                        final_provider_id=provider.id,
                        final_key_id=provider_key.key_id
                    )
                
                except Exception as e:
                    attempt_latency = int((time.time() - attempt_start) * 1000)
                    
                    # Determine error type and whether to retry
                    error_type = type(e).__name__
                    should_retry_key = False
                    should_retry_provider = True
                    
                    if isinstance(e, RateLimitError):
                        error_type = "rate_limit"
                        should_retry_key = False  # Try different key
                        should_retry_provider = True
                    elif isinstance(e, AuthenticationError):
                        error_type = "authentication"
                        should_retry_key = False  # Key is bad
                        should_retry_provider = True
                    elif isinstance(e, QuotaExceededError):
                        error_type = "quota_exceeded"
                        should_retry_key = False
                        should_retry_provider = True
                    elif isinstance(e, ProviderError) and e.status_code and e.status_code >= 500:
                        error_type = "server_error"
                        should_retry_key = True  # Might be temporary
                        should_retry_provider = True
                    else:
                        error_type = "unknown_error"
                        should_retry_key = False
                        should_retry_provider = False
                    
                    # Record failure
                    await key_manager.record_usage(provider_key.id, success=False)
                    await circuit_breaker.record_failure()
                    
                    attempts.append(FallbackAttempt(
                        provider_id=provider.id,
                        provider_name=provider.name,
                        key_id=provider_key.key_id,
                        error_type=error_type,
                        error_message=str(e),
                        status_code=getattr(e, 'status_code', None),
                        latency_ms=attempt_latency,
                        success=False
                    ))
                    
                    attempt_count += 1
                    key_attempts += 1
                    
                    if not should_retry_key:
                        break  # Try next provider
                    
                    if not should_retry_provider:
                        # Fatal error, don't try more providers
                        total_latency = int((time.time() - start_time) * 1000)
                        return FallbackResult(
                            success=False,
                            response=None,
                            attempts=attempts,
                            total_latency_ms=total_latency,
                            final_provider_id=None,
                            final_key_id=None
                        )
        
        # All attempts failed
        total_latency = int((time.time() - start_time) * 1000)
        return FallbackResult(
            success=False,
            response=None,
            attempts=attempts,
            total_latency_ms=total_latency,
            final_provider_id=None,
            final_key_id=None
        )
    
    async def get_provider_health(self, provider_id: int) -> Dict[str, Any]:
        """Get circuit breaker health status for a provider."""
        redis_client = await self._get_redis()
        circuit_breaker = CircuitBreaker(provider_id, redis_client)
        
        state = await circuit_breaker.get_state()
        failure_key = f"circuit_breaker:{provider_id}:failures"
        failures = await redis_client.get(failure_key)
        
        state_key = f"circuit_breaker:{provider_id}:state"
        ttl = await redis_client.ttl(state_key)
        
        return {
            "provider_id": provider_id,
            "circuit_breaker_state": state.value,
            "failure_count": int(failures) if failures else 0,
            "failure_threshold": circuit_breaker.failure_threshold,
            "recovery_timeout_seconds": circuit_breaker.recovery_timeout,
            "state_ttl_seconds": ttl if ttl > 0 else None,
            "can_execute": await circuit_breaker.can_execute()
        }
    
    async def reset_circuit_breaker(self, provider_id: int):
        """Reset circuit breaker for a provider."""
        redis_client = await self._get_redis()
        circuit_breaker = CircuitBreaker(provider_id, redis_client)
        await circuit_breaker.record_success()


# Global fallback engine instance
fallback_engine = FallbackEngine()