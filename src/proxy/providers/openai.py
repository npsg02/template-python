"""OpenAI provider implementation."""

import json
import time
from typing import Dict, Any, List, AsyncIterator, Union
import httpx

from .base import (
    BaseProvider, ProviderType, ProviderRequest, ProviderResponse,
    StreamChunk, EmbeddingRequest, EmbeddingResponse, ProviderError
)


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    def __init__(self, base_url: str = "https://api.openai.com/v1", 
                 api_key: str = "", config: Dict[str, Any] = None):
        super().__init__(base_url, api_key, config)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "OpenAI-Proxy/1.0.0"
        }
    
    async def chat_completion(self, request: ProviderRequest) -> Union[ProviderResponse, AsyncIterator[StreamChunk]]:
        """Generate chat completion using OpenAI Chat API."""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": request.model,
            "messages": request.messages or [],
        }
        
        # Add optional parameters
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.stop is not None:
            payload["stop"] = request.stop
        if request.user is not None:
            payload["user"] = request.user
        if request.stream:
            payload["stream"] = True
        
        # Add any extra parameters
        if request.extra_params:
            payload.update(request.extra_params)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if request.stream:
                return self._stream_chat_completion(client, url, payload)
            else:
                response = await client.post(url, headers=self.headers, json=payload)
                return self._parse_chat_response(response)
    
    async def _stream_chat_completion(self, client: httpx.AsyncClient, 
                                    url: str, payload: Dict[str, Any]) -> AsyncIterator[StreamChunk]:
        """Stream chat completion responses."""
        async with client.stream("POST", url, headers=self.headers, json=payload) as response:
            if response.status_code != 200:
                error_data = await response.aread()
                try:
                    error_json = json.loads(error_data.decode())
                except:
                    error_json = {"error": {"message": error_data.decode()}}
                raise self._handle_error(response.status_code, error_json)
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    if data.strip() == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(data)
                        yield self._parse_stream_chunk(chunk_data)
                    except json.JSONDecodeError:
                        continue  # Skip invalid JSON lines
    
    def _parse_stream_chunk(self, chunk_data: Dict[str, Any]) -> StreamChunk:
        """Parse streaming chunk from OpenAI."""
        choices = chunk_data.get("choices", [])
        if not choices:
            return StreamChunk(raw_chunk=chunk_data)
        
        choice = choices[0]
        delta = choice.get("delta", {})
        
        return StreamChunk(
            content=delta.get("content"),
            finish_reason=choice.get("finish_reason"),
            model=chunk_data.get("model"),
            response_id=chunk_data.get("id"),
            raw_chunk=chunk_data
        )
    
    def _parse_chat_response(self, response: httpx.Response) -> ProviderResponse:
        """Parse chat completion response from OpenAI."""
        if response.status_code != 200:
            error_data = response.json()
            raise self._handle_error(response.status_code, error_data)
        
        data = response.json()
        choices = data.get("choices", [])
        
        if not choices:
            raise ProviderError("No choices in response")
        
        choice = choices[0]
        message = choice.get("message", {})
        
        return ProviderResponse(
            content=message.get("content", ""),
            model=data.get("model", ""),
            usage=data.get("usage"),
            finish_reason=choice.get("finish_reason"),
            response_id=data.get("id"),
            created=data.get("created"),
            raw_response=data
        )
    
    async def completion(self, request: ProviderRequest) -> Union[ProviderResponse, AsyncIterator[StreamChunk]]:
        """Generate text completion using OpenAI Completions API."""
        url = f"{self.base_url}/completions"
        
        payload = {
            "model": request.model,
            "prompt": request.prompt or "",
        }
        
        # Add optional parameters
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.stop is not None:
            payload["stop"] = request.stop
        if request.user is not None:
            payload["user"] = request.user
        if request.stream:
            payload["stream"] = True
        
        # Add any extra parameters
        if request.extra_params:
            payload.update(request.extra_params)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if request.stream:
                return self._stream_completion(client, url, payload)
            else:
                response = await client.post(url, headers=self.headers, json=payload)
                return self._parse_completion_response(response)
    
    async def _stream_completion(self, client: httpx.AsyncClient, 
                               url: str, payload: Dict[str, Any]) -> AsyncIterator[StreamChunk]:
        """Stream completion responses."""
        async with client.stream("POST", url, headers=self.headers, json=payload) as response:
            if response.status_code != 200:
                error_data = await response.aread()
                try:
                    error_json = json.loads(error_data.decode())
                except:
                    error_json = {"error": {"message": error_data.decode()}}
                raise self._handle_error(response.status_code, error_json)
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    if data.strip() == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(data)
                        yield self._parse_completion_stream_chunk(chunk_data)
                    except json.JSONDecodeError:
                        continue  # Skip invalid JSON lines
    
    def _parse_completion_stream_chunk(self, chunk_data: Dict[str, Any]) -> StreamChunk:
        """Parse streaming chunk from OpenAI completion."""
        choices = chunk_data.get("choices", [])
        if not choices:
            return StreamChunk(raw_chunk=chunk_data)
        
        choice = choices[0]
        
        return StreamChunk(
            content=choice.get("text"),
            finish_reason=choice.get("finish_reason"),
            model=chunk_data.get("model"),
            response_id=chunk_data.get("id"),
            raw_chunk=chunk_data
        )
    
    def _parse_completion_response(self, response: httpx.Response) -> ProviderResponse:
        """Parse completion response from OpenAI."""
        if response.status_code != 200:
            error_data = response.json()
            raise self._handle_error(response.status_code, error_data)
        
        data = response.json()
        choices = data.get("choices", [])
        
        if not choices:
            raise ProviderError("No choices in response")
        
        choice = choices[0]
        
        return ProviderResponse(
            content=choice.get("text", ""),
            model=data.get("model", ""),
            usage=data.get("usage"),
            finish_reason=choice.get("finish_reason"),
            response_id=data.get("id"),
            created=data.get("created"),
            raw_response=data
        )
    
    async def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings using OpenAI Embeddings API."""
        url = f"{self.base_url}/embeddings"
        
        payload = {
            "model": request.model,
            "input": request.input,
        }
        
        if request.user:
            payload["user"] = request.user
        if request.encoding_format:
            payload["encoding_format"] = request.encoding_format
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            
            if response.status_code != 200:
                error_data = response.json()
                raise self._handle_error(response.status_code, error_data)
            
            data = response.json()
            embeddings = [item["embedding"] for item in data.get("data", [])]
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model=data.get("model", ""),
                usage=data.get("usage", {}),
                raw_response=data
            )
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models from OpenAI."""
        url = f"{self.base_url}/models"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                error_data = response.json()
                raise self._handle_error(response.status_code, error_data)
            
            data = response.json()
            return data.get("data", [])