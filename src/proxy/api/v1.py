"""OpenAI-compatible v1 API routes."""

import json
import uuid
import time
from typing import Dict, Any, AsyncIterator
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from .models import (
    ChatCompletionRequest, CompletionRequest, EmbeddingRequest,
    ChatCompletionResponse, CompletionResponse, EmbeddingResponse,
    ChatCompletionChunk, ModelListResponse, ModelInfo, ErrorResponse,
    ChatCompletionChoice, CompletionChoice, EmbeddingData, Usage,
    ChatMessage
)
from ..providers.base import ProviderRequest, EmbeddingRequest as ProviderEmbeddingRequest
from ..providers.openai import OpenAIProvider
from ..providers.mock import MockProvider
from ..core.fallback import fallback_engine
from ..core.model_mapper import model_mapper
from ..core.key_manager import key_manager
from ..api.middleware import proxy_logger
from ..models import Provider


router = APIRouter(prefix="/v1", tags=["OpenAI Compatible API"])


def create_provider_instance(provider: Provider, api_key: str):
    """Factory function to create provider instances."""
    if provider.provider_type == "openai":
        return OpenAIProvider(provider.base_url, api_key, provider.config_json)
    elif provider.provider_type == "mock" or provider.provider_type == "custom":
        return MockProvider(provider.base_url, api_key, provider.config_json)
    else:
        raise ValueError(f"Unsupported provider type: {provider.provider_type}")


async def stream_chat_completion_response(chunks: AsyncIterator, request_id: str) -> AsyncIterator[str]:
    """Stream chat completion chunks in OpenAI format."""
    try:
        async for chunk in chunks:
            if chunk.content is not None or chunk.finish_reason is not None:
                # Create OpenAI-compatible chunk
                openai_chunk = ChatCompletionChunk(
                    id=request_id,
                    model=chunk.model or "unknown",
                    choices=[{
                        "index": 0,
                        "delta": {
                            "content": chunk.content
                        } if chunk.content else {},
                        "finish_reason": chunk.finish_reason
                    }],
                    usage=chunk.usage if chunk.finish_reason else None
                )
                
                yield f"data: {openai_chunk.model_dump_json()}\n\n"
        
        # Send final [DONE] message
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        # Send error in stream
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "stream_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"


def record_token_usage(api_key: str, usage: Dict[str, int]):
    """Background task to record token usage."""
    if usage and usage.get('total_tokens', 0) > 0:
        # This would be called as a background task
        pass


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request
) -> ChatCompletionResponse:
    """Create chat completion."""
    request_id = getattr(http_request.state, 'request_id', str(uuid.uuid4()))
    
    # Store model alias in request state for audit
    http_request.state.model_alias = request.model
    
    # Convert to provider request
    provider_request = ProviderRequest(
        model=request.model,
        messages=[msg.model_dump() for msg in request.messages],
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
        frequency_penalty=request.frequency_penalty,
        presence_penalty=request.presence_penalty,
        stop=request.stop,
        stream=request.stream,
        user=request.user
    )
    
    # Execute with fallback
    result = await fallback_engine.execute_with_fallback(
        model_alias=request.model,
        request=provider_request,
        provider_factory=create_provider_instance
    )
    
    # Store audit information
    http_request.state.fallback_chain = [
        {
            "provider_id": attempt.provider_id,
            "provider_name": attempt.provider_name,
            "key_id": attempt.key_id,
            "success": attempt.success,
            "error_type": attempt.error_type,
            "latency_ms": attempt.latency_ms
        }
        for attempt in result.attempts
    ]
    
    if result.final_provider_id:
        http_request.state.provider_id = result.final_provider_id
    if result.final_key_id:
        http_request.state.key_id = result.final_key_id
    
    if not result.success:
        # Return error based on last attempt
        last_attempt = result.attempts[-1] if result.attempts else None
        error_message = last_attempt.error_message if last_attempt else "All providers failed"
        status_code = last_attempt.status_code if last_attempt and last_attempt.status_code else 500
        
        proxy_logger.log(
            "ERROR",
            "Chat completion failed",
            request_id=request_id,
            model=request.model,
            attempts=len(result.attempts),
            total_latency_ms=result.total_latency_ms,
            error_message=error_message
        )
        
        raise HTTPException(
            status_code=status_code,
            detail=error_message
        )
    
    # Handle streaming response
    if request.stream:
        proxy_logger.log(
            "INFO",
            "Starting chat completion stream",
            request_id=request_id,
            model=request.model,
            provider_id=result.final_provider_id
        )
        
        return StreamingResponse(
            stream_chat_completion_response(result.response, request_id),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    # Handle regular response
    provider_response = result.response
    
    # Store token usage for audit
    if provider_response.usage:
        http_request.state.token_usage = provider_response.usage
    
    # Convert to OpenAI format
    openai_response = ChatCompletionResponse(
        id=request_id,
        model=provider_response.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(
                    role="assistant",
                    content=provider_response.content
                ),
                finish_reason=provider_response.finish_reason
            )
        ],
        usage=Usage(**provider_response.usage) if provider_response.usage else None
    )
    
    proxy_logger.log(
        "INFO",
        "Chat completion completed",
        request_id=request_id,
        model=request.model,
        provider_id=result.final_provider_id,
        total_latency_ms=result.total_latency_ms,
        usage=provider_response.usage
    )
    
    return openai_response


@router.post("/completions")
async def completions(
    request: CompletionRequest,
    http_request: Request
) -> CompletionResponse:
    """Create text completion."""
    request_id = getattr(http_request.state, 'request_id', str(uuid.uuid4()))
    
    # Store model alias in request state for audit
    http_request.state.model_alias = request.model
    
    # Convert to provider request
    provider_request = ProviderRequest(
        model=request.model,
        prompt=request.prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
        frequency_penalty=request.frequency_penalty,
        presence_penalty=request.presence_penalty,
        stop=request.stop,
        stream=request.stream,
        user=request.user
    )
    
    # Execute with fallback
    result = await fallback_engine.execute_with_fallback(
        model_alias=request.model,
        request=provider_request,
        provider_factory=create_provider_instance
    )
    
    # Store audit information
    http_request.state.fallback_chain = [
        {
            "provider_id": attempt.provider_id,
            "provider_name": attempt.provider_name,
            "key_id": attempt.key_id,
            "success": attempt.success,
            "error_type": attempt.error_type,
            "latency_ms": attempt.latency_ms
        }
        for attempt in result.attempts
    ]
    
    if result.final_provider_id:
        http_request.state.provider_id = result.final_provider_id
    if result.final_key_id:
        http_request.state.key_id = result.final_key_id
    
    if not result.success:
        # Return error based on last attempt
        last_attempt = result.attempts[-1] if result.attempts else None
        error_message = last_attempt.error_message if last_attempt else "All providers failed"
        status_code = last_attempt.status_code if last_attempt and last_attempt.status_code else 500
        
        raise HTTPException(
            status_code=status_code,
            detail=error_message
        )
    
    # Handle streaming response (similar to chat completions)
    if request.stream:
        # Implementation would be similar to chat completion streaming
        # For brevity, returning error for now
        raise HTTPException(
            status_code=501,
            detail="Streaming not implemented for completions endpoint"
        )
    
    # Handle regular response
    provider_response = result.response
    
    # Store token usage for audit
    if provider_response.usage:
        http_request.state.token_usage = provider_response.usage
    
    # Convert to OpenAI format
    openai_response = CompletionResponse(
        id=request_id,
        model=provider_response.model,
        choices=[
            CompletionChoice(
                index=0,
                text=provider_response.content,
                finish_reason=provider_response.finish_reason
            )
        ],
        usage=Usage(**provider_response.usage) if provider_response.usage else None
    )
    
    return openai_response


@router.post("/embeddings")
async def embeddings(
    request: EmbeddingRequest,
    http_request: Request
) -> EmbeddingResponse:
    """Create embeddings."""
    request_id = getattr(http_request.state, 'request_id', str(uuid.uuid4()))
    
    # Store model alias in request state for audit
    http_request.state.model_alias = request.model
    
    # Get provider mapping
    mapping = model_mapper.get_default_mapping(request.model)
    if not mapping:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{request.model}' not found"
        )
    
    provider, provider_model_name, config = mapping
    
    # Get API key
    provider_key = await key_manager.select_key(provider.id)
    if not provider_key:
        raise HTTPException(
            status_code=503,
            detail="No available API keys for this model"
        )
    
    # Create provider instance
    api_key = key_manager.get_decrypted_key(provider_key)
    provider_instance = create_provider_instance(provider, api_key)
    
    # Convert to provider request
    provider_request = ProviderEmbeddingRequest(
        model=provider_model_name,
        input=request.input,
        user=request.user,
        encoding_format=request.encoding_format
    )
    
    try:
        # Execute request
        provider_response = await provider_instance.embedding(provider_request)
        
        # Record success
        await key_manager.record_usage(provider_key.id, success=True)
        
        # Store audit information
        http_request.state.provider_id = provider.id
        http_request.state.key_id = provider_key.key_id
        if provider_response.usage:
            http_request.state.token_usage = provider_response.usage
        
        # Convert to OpenAI format
        embedding_data = [
            EmbeddingData(
                embedding=embedding,
                index=i
            )
            for i, embedding in enumerate(provider_response.embeddings)
        ]
        
        openai_response = EmbeddingResponse(
            data=embedding_data,
            model=provider_response.model,
            usage=Usage(**provider_response.usage)
        )
        
        return openai_response
        
    except Exception as e:
        # Record failure
        await key_manager.record_usage(provider_key.id, success=False)
        
        proxy_logger.log(
            "ERROR",
            "Embedding request failed",
            request_id=request_id,
            model=request.model,
            provider_id=provider.id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/models")
async def list_models() -> ModelListResponse:
    """List available models."""
    # Get all model aliases from mappings
    model_aliases = model_mapper.get_available_models()
    
    # Create model info for each alias
    model_data = [
        ModelInfo(
            id=alias,
            owned_by="proxy"
        )
        for alias in model_aliases
    ]
    
    return ModelListResponse(data=model_data)