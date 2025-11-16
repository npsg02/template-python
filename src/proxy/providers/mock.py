"""Mock provider for testing and development."""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, AsyncIterator, Union

from .base import (
    BaseProvider, ProviderType, ProviderRequest, ProviderResponse,
    StreamChunk, EmbeddingRequest, EmbeddingResponse
)


class MockProvider(BaseProvider):
    """Mock provider for testing and development."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CUSTOM
    
    def __init__(self, base_url: str = "http://localhost:8080", 
                 api_key: str = "mock-key", config: Dict[str, Any] = None):
        super().__init__(base_url, api_key, config)
        self.simulate_delay = config.get("simulate_delay", 0.1) if config else 0.1
        self.failure_rate = config.get("failure_rate", 0.0) if config else 0.0
    
    async def chat_completion(self, request: ProviderRequest) -> Union[ProviderResponse, AsyncIterator[StreamChunk]]:
        """Generate mock chat completion."""
        await asyncio.sleep(self.simulate_delay)
        
        # Simulate failures
        if self.failure_rate > 0 and hash(time.time()) % 100 < self.failure_rate * 100:
            from .base import ProviderError
            raise ProviderError("Simulated provider failure", 500, "internal_error")
        
        if request.stream:
            return self._stream_chat_completion(request)
        else:
            return self._generate_chat_response(request)
    
    async def _stream_chat_completion(self, request: ProviderRequest) -> AsyncIterator[StreamChunk]:
        """Generate streaming mock chat completion."""
        response_text = f"This is a mock response to: {request.messages[-1]['content'] if request.messages else 'no message'}"
        response_id = str(uuid.uuid4())
        
        # Split response into chunks
        words = response_text.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.05)  # Small delay between chunks
            
            chunk = StreamChunk(
                content=word + " " if i < len(words) - 1 else word,
                model=request.model,
                response_id=response_id,
                raw_chunk={
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": word + " " if i < len(words) - 1 else word},
                        "finish_reason": None
                    }]
                }
            )
            yield chunk
        
        # Final chunk with finish_reason
        final_chunk = StreamChunk(
            content="",
            finish_reason="stop",
            model=request.model,
            response_id=response_id,
            usage={"prompt_tokens": 10, "completion_tokens": len(words), "total_tokens": 10 + len(words)},
            raw_chunk={
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": len(words), "total_tokens": 10 + len(words)}
            }
        )
        yield final_chunk
    
    def _generate_chat_response(self, request: ProviderRequest) -> ProviderResponse:
        """Generate mock chat response."""
        content = f"This is a mock response to: {request.messages[-1]['content'] if request.messages else 'no message'}"
        
        return ProviderResponse(
            content=content,
            model=request.model,
            usage={"prompt_tokens": 10, "completion_tokens": len(content.split()), "total_tokens": 10 + len(content.split())},
            finish_reason="stop",
            response_id=str(uuid.uuid4()),
            created=int(time.time()),
            raw_response={
                "id": str(uuid.uuid4()),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": len(content.split()), "total_tokens": 10 + len(content.split())}
            }
        )
    
    async def completion(self, request: ProviderRequest) -> Union[ProviderResponse, AsyncIterator[StreamChunk]]:
        """Generate mock text completion."""
        await asyncio.sleep(self.simulate_delay)
        
        # Simulate failures
        if self.failure_rate > 0 and hash(time.time()) % 100 < self.failure_rate * 100:
            from .base import ProviderError
            raise ProviderError("Simulated provider failure", 500, "internal_error")
        
        if request.stream:
            return self._stream_completion(request)
        else:
            return self._generate_completion_response(request)
    
    async def _stream_completion(self, request: ProviderRequest) -> AsyncIterator[StreamChunk]:
        """Generate streaming mock completion."""
        response_text = f"Mock completion for: {request.prompt or 'no prompt'}"
        response_id = str(uuid.uuid4())
        
        # Split response into chunks
        words = response_text.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.05)  # Small delay between chunks
            
            chunk = StreamChunk(
                content=word + " " if i < len(words) - 1 else word,
                model=request.model,
                response_id=response_id,
                raw_chunk={
                    "id": response_id,
                    "object": "text_completion",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "text": word + " " if i < len(words) - 1 else word,
                        "index": 0,
                        "finish_reason": None
                    }]
                }
            )
            yield chunk
        
        # Final chunk
        final_chunk = StreamChunk(
            content="",
            finish_reason="stop",
            model=request.model,
            response_id=response_id,
            usage={"prompt_tokens": 5, "completion_tokens": len(words), "total_tokens": 5 + len(words)},
            raw_chunk={
                "id": response_id,
                "object": "text_completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "text": "",
                    "index": 0,
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 5, "completion_tokens": len(words), "total_tokens": 5 + len(words)}
            }
        )
        yield final_chunk
    
    def _generate_completion_response(self, request: ProviderRequest) -> ProviderResponse:
        """Generate mock completion response."""
        content = f"Mock completion for: {request.prompt or 'no prompt'}"
        
        return ProviderResponse(
            content=content,
            model=request.model,
            usage={"prompt_tokens": 5, "completion_tokens": len(content.split()), "total_tokens": 5 + len(content.split())},
            finish_reason="stop",
            response_id=str(uuid.uuid4()),
            created=int(time.time()),
            raw_response={
                "id": str(uuid.uuid4()),
                "object": "text_completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "text": content,
                    "index": 0,
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 5, "completion_tokens": len(content.split()), "total_tokens": 5 + len(content.split())}
            }
        )
    
    async def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate mock embeddings."""
        await asyncio.sleep(self.simulate_delay)
        
        # Generate mock embeddings (512-dimensional vectors)
        inputs = request.input if isinstance(request.input, list) else [request.input]
        embeddings = []
        
        for text in inputs:
            # Create a simple hash-based mock embedding
            embedding = [float(hash(f"{text}_{i}") % 1000) / 1000.0 for i in range(512)]
            embeddings.append(embedding)
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model=request.model,
            usage={"prompt_tokens": sum(len(text.split()) for text in inputs), "total_tokens": sum(len(text.split()) for text in inputs)},
            raw_response={
                "object": "list",
                "data": [
                    {
                        "object": "embedding",
                        "embedding": emb,
                        "index": i
                    }
                    for i, emb in enumerate(embeddings)
                ],
                "model": request.model,
                "usage": {"prompt_tokens": sum(len(text.split()) for text in inputs), "total_tokens": sum(len(text.split()) for text in inputs)}
            }
        )
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List mock available models."""
        await asyncio.sleep(self.simulate_delay)
        
        return [
            {
                "id": "mock-gpt-3.5-turbo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "mock-provider"
            },
            {
                "id": "mock-gpt-4",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "mock-provider"
            },
            {
                "id": "mock-text-embedding-ada-002",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "mock-provider"
            }
        ]