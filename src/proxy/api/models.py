"""Pydantic models for API requests and responses."""

from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
import time


class ChatMessage(BaseModel):
    """Chat message model."""
    role: Literal["system", "user", "assistant", "function"] = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")
    name: Optional[str] = Field(None, description="Name of the function (for function role)")


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions."""
    model: str = Field(..., description="Model to use for completion")
    messages: List[ChatMessage] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(None, ge=0, le=1, description="Top-p sampling parameter")
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    stream: Optional[bool] = Field(False, description="Enable streaming")
    user: Optional[str] = Field(None, description="User identifier")


class CompletionRequest(BaseModel):
    """Request model for text completions."""
    model: str = Field(..., description="Model to use for completion")
    prompt: str = Field(..., description="Text prompt")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(None, ge=0, le=1, description="Top-p sampling parameter")
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    stream: Optional[bool] = Field(False, description="Enable streaming")
    user: Optional[str] = Field(None, description="User identifier")


class EmbeddingRequest(BaseModel):
    """Request model for embeddings."""
    model: str = Field(..., description="Model to use for embeddings")
    input: Union[str, List[str]] = Field(..., description="Input text(s)")
    user: Optional[str] = Field(None, description="User identifier")
    encoding_format: Optional[str] = Field("float", description="Encoding format")


class Usage(BaseModel):
    """Token usage information."""
    prompt_tokens: int = Field(..., description="Tokens in the prompt")
    completion_tokens: Optional[int] = Field(None, description="Tokens in the completion")
    total_tokens: int = Field(..., description="Total tokens used")


class ChatCompletionChoice(BaseModel):
    """Choice in chat completion response."""
    index: int = Field(..., description="Choice index")
    message: ChatMessage = Field(..., description="Generated message")
    finish_reason: Optional[str] = Field(None, description="Reason for completion finish")


class CompletionChoice(BaseModel):
    """Choice in text completion response."""
    index: int = Field(..., description="Choice index")
    text: str = Field(..., description="Generated text")
    finish_reason: Optional[str] = Field(None, description="Reason for completion finish")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completions."""
    id: str = Field(..., description="Response ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[ChatCompletionChoice] = Field(..., description="Generated choices")
    usage: Optional[Usage] = Field(None, description="Token usage")


class CompletionResponse(BaseModel):
    """Response model for text completions."""
    id: str = Field(..., description="Response ID")
    object: str = Field("text_completion", description="Object type")
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[CompletionChoice] = Field(..., description="Generated choices")
    usage: Optional[Usage] = Field(None, description="Token usage")


class ChatCompletionChunk(BaseModel):
    """Streaming chunk for chat completions."""
    id: str = Field(..., description="Response ID")
    object: str = Field("chat.completion.chunk", description="Object type")
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Dict[str, Any]] = Field(..., description="Streaming choices")
    usage: Optional[Usage] = Field(None, description="Token usage (final chunk only)")


class EmbeddingData(BaseModel):
    """Embedding data object."""
    object: str = Field("embedding", description="Object type")
    embedding: List[float] = Field(..., description="Embedding vector")
    index: int = Field(..., description="Input index")


class EmbeddingResponse(BaseModel):
    """Response model for embeddings."""
    object: str = Field("list", description="Object type")
    data: List[EmbeddingData] = Field(..., description="Embedding data")
    model: str = Field(..., description="Model used")
    usage: Usage = Field(..., description="Token usage")


class ModelInfo(BaseModel):
    """Model information."""
    id: str = Field(..., description="Model ID")
    object: str = Field("model", description="Object type")
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    owned_by: str = Field(..., description="Organization that owns the model")


class ModelListResponse(BaseModel):
    """Response model for model list."""
    object: str = Field("list", description="Object type")
    data: List[ModelInfo] = Field(..., description="Available models")


class ErrorDetail(BaseModel):
    """Error detail information."""
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    param: Optional[str] = Field(None, description="Parameter that caused the error")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: ErrorDetail = Field(..., description="Error details")