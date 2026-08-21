"""
JARVIS Web API Pydantic Schemas Module.

Defines typed request and response data models for REST API endpoints and WebSocket events.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    """JARVIS Assistant & Subsystems Status Response."""
    online: bool = Field(..., description="Whether the assistant core is online and active")
    state: str = Field(..., description="Current SpeechState enum value (e.g. WAKING, LISTENING)")
    microphone_status: str = Field(..., description="Active microphone backend status")
    stt_status: str = Field(..., description="Faster-Whisper STT status")
    tts_status: str = Field(..., description="Kokoro/Piper TTS status")
    ollama_status: str = Field(..., description="Ollama LLM connectivity status")
    llm_model: str = Field(..., description="Configured LLM model identifier")
    uptime_seconds: float = Field(..., description="System uptime in seconds")


class ToolInfo(BaseModel):
    """Information regarding a registered tool."""
    name: str = Field(..., description="Tool unique name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameter schema map")


class ToolsListResponse(BaseModel):
    """Registered tools and recent tool execution history."""
    total_tools: int = Field(..., description="Number of registered tools")
    tools: List[ToolInfo] = Field(default_factory=list, description="List of registered tools")
    execution_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent tool executions")


class MemoryItem(BaseModel):
    """Persistent memory record item."""
    key: str = Field(..., description="Fact key identifier")
    value: Any = Field(..., description="Fact or preference value")
    timestamp: Optional[float] = Field(None, description="Storage UNIX timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")


class MemoryListResponse(BaseModel):
    """Persistent and short-term memory status."""
    persistent_count: int = Field(..., description="Total persistent memories stored")
    short_term_count: int = Field(..., description="Current short-term history length")
    memories: Dict[str, Any] = Field(default_factory=dict, description="Key-value persistent memories")


class RememberRequest(BaseModel):
    """Request payload to store a new fact in persistent memory."""
    key: str = Field(..., min_length=1, description="Unique key for the fact")
    value: Any = Field(..., description="Fact or preference value")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata dict")


class ForgetRequest(BaseModel):
    """Request payload to remove a fact from persistent memory."""
    key: str = Field(..., min_length=1, description="Memory key to delete")


class ChatRequest(BaseModel):
    """Text chat prompt request."""
    message: str = Field(..., min_length=1, description="User text prompt")


class ChatResponse(BaseModel):
    """Assistant chat response."""
    user_text: str = Field(..., description="User prompt text")
    assistant_response: str = Field(..., description="Generated JARVIS response")
    timestamp: str = Field(..., description="ISO timestamp")


class SystemDiagnosticsResponse(BaseModel):
    """Host system diagnostics and environment metrics."""
    cpu_load: Dict[str, float] = Field(..., description="1, 5, 15 minute CPU load averages")
    memory: Dict[str, float] = Field(..., description="RAM statistics in GB and percent used")
    disk: Dict[str, float] = Field(..., description="Disk space statistics in GB")
    uptime_seconds: float = Field(..., description="Host uptime in seconds")
    python_version: str = Field(..., description="Python runtime version")
    jarvis_version: str = Field(..., description="JARVIS release version")
    ollama_connected: bool = Field(..., description="Whether Ollama REST API is accessible")


class ControlRequest(BaseModel):
    """Assistant runtime control action request."""
    action: str = Field(..., description="Runtime action: 'start', 'stop', 'restart', or 'clear_memory'")


class ControlResponse(BaseModel):
    """Assistant runtime control response."""
    success: bool = Field(..., description="Whether control action succeeded")
    message: str = Field(..., description="Status explanation message")


class WebSocketEvent(BaseModel):
    """Structured event format broadcast over WebSockets."""
    type: str = Field(..., description="Event type name (e.g., state_change, transcription)")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Primary event payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")
