"""Middleware for the proxy API."""

import time
import uuid
import json
import logging
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import User, RequestAudit
from ..models.database import get_db_session
from ..core.rate_limiter import global_rate_limiter


# Configure structured logging
class StructuredLogger:
    """Structured JSON logger."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log(self, level: str, message: str, **kwargs):
        """Log structured message."""
        log_data = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs
        }
        
        if level.upper() == "ERROR":
            self.logger.error(json.dumps(log_data))
        elif level.upper() == "WARNING":
            self.logger.warning(json.dumps(log_data))
        elif level.upper() == "INFO":
            self.logger.info(json.dumps(log_data))
        else:
            self.logger.debug(json.dumps(log_data))


# Global logger instance
proxy_logger = StructuredLogger("openai_proxy")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Add to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Proxy-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get request details
        request_id = getattr(request.state, 'request_id', 'unknown')
        client_ip = request.client.host if request.client else 'unknown'
        user_agent = request.headers.get('user-agent', 'unknown')
        
        # Log request
        proxy_logger.log(
            "INFO",
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log response
            proxy_logger.log(
                "INFO",
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                latency_ms=latency_ms
            )
            
            return response
            
        except Exception as e:
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            proxy_logger.log(
                "ERROR",
                "Request failed",
                request_id=request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                latency_ms=latency_ms
            )
            
            raise


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Handle API key authentication."""
    
    PROTECTED_PATHS = ['/v1/', '/admin/']
    PUBLIC_PATHS = ['/docs', '/redoc', '/openapi.json', '/health', '/metrics']
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public paths
        path = request.url.path
        if any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # Check if path requires authentication
        if not any(path.startswith(protected_path) for protected_path in self.PROTECTED_PATHS):
            return await call_next(request)
        
        # Get API key from Authorization header
        auth_header = request.headers.get('authorization', '')
        
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header"
            )
        
        # Parse Bearer token
        try:
            scheme, token = auth_header.split(' ', 1)
            if scheme.lower() != 'bearer':
                raise ValueError("Invalid scheme")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        # For admin endpoints, validate user API key
        if path.startswith('/admin/'):
            user = await self._validate_admin_token(token)
            request.state.user = user
        else:
            # For proxy endpoints, just store the token for provider forwarding
            request.state.api_key = token
        
        return await call_next(request)
    
    async def _validate_admin_token(self, token: str) -> User:
        """Validate admin API token."""
        with get_db_session() as db:
            user = db.query(User).filter(
                User.api_key == token,
                User.is_active == True
            ).first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            
            if not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            
            return user


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for certain paths
        path = request.url.path
        if path in ['/health', '/metrics', '/docs', '/redoc', '/openapi.json']:
            return await call_next(request)
        
        # Get identifiers
        api_key = getattr(request.state, 'api_key', None)
        client_ip = request.client.host if request.client else None
        
        # Check rate limits
        rate_limit_results = await global_rate_limiter.check_request_limits(
            api_key=api_key,
            ip_address=client_ip,
            estimated_tokens=100  # Rough estimate for now
        )
        
        # Check if any limits are exceeded
        for limit_name, result in rate_limit_results.items():
            if not result.allowed:
                # Log rate limit exceeded
                proxy_logger.log(
                    "WARNING",
                    "Rate limit exceeded",
                    request_id=getattr(request.state, 'request_id', 'unknown'),
                    limit_type=limit_name,
                    identifier=api_key if 'key' in limit_name else client_ip,
                    retry_after=result.retry_after
                )
                
                # Return rate limit error
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {limit_name}",
                    headers={"Retry-After": str(result.retry_after)} if result.retry_after else None
                )
        
        return await call_next(request)


class AuditMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware."""
    
    async def dispatch(self, request: Request, call_next):
        # Only audit API requests
        path = request.url.path
        if not path.startswith('/v1/'):
            return await call_next(request)
        
        start_time = time.time()
        
        # Get request details
        request_id = getattr(request.state, 'request_id', 'unknown')
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')
        api_key = getattr(request.state, 'api_key', None)
        
        # Process request
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Create audit record (in background)
        try:
            with get_db_session() as db:
                audit_record = RequestAudit(
                    request_id=request_id,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    endpoint=path,
                    method=request.method,
                    status_code=response.status_code,
                    latency_ms=latency_ms
                )
                
                # Add additional details if available
                if hasattr(request.state, 'model_alias'):
                    audit_record.model_alias = request.state.model_alias
                if hasattr(request.state, 'provider_id'):
                    audit_record.provider_id = request.state.provider_id
                if hasattr(request.state, 'key_id'):
                    audit_record.key_id = request.state.key_id
                if hasattr(request.state, 'fallback_chain'):
                    audit_record.fallback_chain_json = request.state.fallback_chain
                if hasattr(request.state, 'token_usage'):
                    usage = request.state.token_usage
                    audit_record.input_tokens = usage.get('prompt_tokens')
                    audit_record.output_tokens = usage.get('completion_tokens')
                    audit_record.total_tokens = usage.get('total_tokens')
                
                db.add(audit_record)
                db.commit()
                
        except Exception as e:
            # Log audit failure but don't fail the request
            proxy_logger.log(
                "ERROR",
                "Failed to create audit record",
                request_id=request_id,
                error=str(e)
            )
        
        return response