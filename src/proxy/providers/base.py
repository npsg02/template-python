"""Base provider interface and common types."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncIterator, Union
from dataclasses import dataclass
from enum import Enum
import json


class ProviderType(str, Enum):
    """Supported provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class ProviderRequest:
    """Standardized request format for providers."""
    model: str
    messages: Optional[List[Dict[str, Any]]] = None
    prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None
    stream: bool = False
    user: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None


@dataclass
class ProviderResponse:
    """Standardized response format from providers."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    response_id: Optional[str] = None
    created: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class StreamChunk:
    """Streaming response chunk."""
    content: Optional[str] = None
    finish_reason: Optional[str] = None
    model: Optional[str] = None
    response_id: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    raw_chunk: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingRequest:
    """Request for embeddings."""
    input: Union[str, List[str]]
    model: str
    user: Optional[str] = None
    encoding_format: str = "float"


@dataclass
class EmbeddingResponse:
    """Response from embedding request."""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]
    raw_response: Optional[Dict[str, Any]] = None


class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 error_type: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type


class RateLimitError(ProviderError):
    """Rate limit exceeded error."""
    pass


class AuthenticationError(ProviderError):
    """Authentication failed error."""
    pass


class ModelNotFoundError(ProviderError):
    """Model not found error."""
    pass


class QuotaExceededError(ProviderError):
    """Quota exceeded error."""
    pass


class BaseProvider(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, base_url: str, api_key: str, config: Optional[Dict[str, Any]] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        pass
    
    @abstractmethod
    async def chat_completion(self, request: ProviderRequest) -> Union[ProviderResponse, AsyncIterator[StreamChunk]]:
        """Generate chat completion."""
        pass
    
    @abstractmethod
    async def completion(self, request: ProviderRequest) -> Union[ProviderResponse, AsyncIterator[StreamChunk]]:
        """Generate text completion (legacy endpoint)."""
        pass
    
    @abstractmethod
    async def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings."""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        pass
    
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception:
            return False
    
    def _handle_error(self, status_code: int, response_data: Dict[str, Any]) -> ProviderError:
        """Convert HTTP errors to provider errors."""
        error_message = response_data.get("error", {}).get("message", "Unknown error")
        error_type = response_data.get("error", {}).get("type", "unknown")
        
        if status_code == 401:
            return AuthenticationError(error_message, status_code, error_type)
        elif status_code == 404:
            return ModelNotFoundError(error_message, status_code, error_type)
        elif status_code == 429:
            return RateLimitError(error_message, status_code, error_type)
        elif status_code == 402:
            return QuotaExceededError(error_message, status_code, error_type)
        else:
            return ProviderError(error_message, status_code, error_type)