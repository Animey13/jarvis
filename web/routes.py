"""
JARVIS Web Dashboard REST API Routes.

Implements clean REST API endpoints communicating with existing JARVIS application
components via clean abstractions.
"""

from datetime import datetime, timezone
import logging
import platform
import sys
from typing import Any, Dict, List
import httpx
from fastapi import APIRouter, HTTPException, status

from config.config import settings
from memory.manager import MemoryManager
from tools.system_tools import SystemStatusTool
from web.schemas import (
    ChatRequest,
    ChatResponse,
    ControlRequest,
    ControlResponse,
    MemoryListResponse,
    RememberRequest,
    StatusResponse,
    SystemDiagnosticsResponse,
    ToolInfo,
    ToolsListResponse,
)
from web.state import event_bus, web_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jarvis"])


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """
    Returns real-time status metrics of JARVIS assistant subsystems.
    """
    online = web_state.assistant.is_running if web_state.assistant else False
    speech_state = web_state.speech_manager.state.value if web_state.speech_manager else "OFFLINE"

    mic_status = "simulated"
    if web_state.speech_manager and web_state.speech_manager.microphone:
        mic_status = "active" if not web_state.speech_manager.microphone.use_simulator else "simulated"

    stt_status = "available" if (web_state.speech_manager and web_state.speech_manager.recognizer and web_state.speech_manager.recognizer.model is not None) else "simulation_fallback"
    tts_status = "available" if web_state.speech_manager else "simulated"

    # Check Ollama connectivity
    ollama_status = "disconnected"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.llm.api_base}/api/tags")
            if resp.status_code == 200:
                ollama_status = "connected"
    except Exception:
        ollama_status = "disconnected"

    return StatusResponse(
        online=online,
        state=speech_state,
        microphone_status=mic_status,
        stt_status=stt_status,
        tts_status=tts_status,
        ollama_status=ollama_status,
        llm_model=settings.llm.model,
        uptime_seconds=web_state.get_uptime_seconds()
    )


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """
    Returns sanitized active configuration settings.
    """
    return {
        "app": {
            "name": settings.app.name,
            "env": settings.app.env,
            "debug": settings.app.debug,
        },
        "llm": {
            "provider": settings.llm.provider,
            "model": settings.llm.model,
            "api_base": settings.llm.api_base,
            "timeout": settings.llm.timeout,
        },
        "speech": {
            "input_device": settings.speech.input_device,
            "tts_provider": settings.speech.tts_provider,
            "voice_id": settings.speech.voice_id,
        },
        "microphone": {
            "device": settings.microphone.device,
            "sample_rate": settings.microphone.sample_rate,
            "channels": settings.microphone.channels,
            "use_simulator": settings.microphone.use_simulator,
        },
        "vad": {
            "sensitivity": settings.vad.sensitivity,
            "silence_timeout": settings.vad.silence_timeout,
            "min_speech_duration": settings.vad.min_speech_duration,
        },
        "whisper": {
            "model": settings.whisper.model,
            "language": settings.whisper.language,
            "compute_type": settings.whisper.compute_type,
            "use_gpu": settings.whisper.use_gpu,
        },
        "wakeword": {
            "phrase": settings.wakeword.phrase,
            "cooldown": settings.wakeword.cooldown,
        },
    }


@router.get("/tools", response_model=ToolsListResponse)
async def get_tools() -> ToolsListResponse:
    """
    Returns registered tools and recent execution log feed.
    """
    tool_registry = web_state.tool_registry
    tools_list: List[ToolInfo] = []

    if tool_registry:
        for t in tool_registry.get_all_tools():
            tools_list.append(ToolInfo(
                name=t.name,
                description=t.description,
                parameters=t.parameters
            ))

    return ToolsListResponse(
        total_tools=len(tools_list),
        tools=tools_list,
        execution_history=web_state.tool_execution_history
    )


@router.get("/memory", response_model=MemoryListResponse)
async def get_memory() -> MemoryListResponse:
    """
    Returns persistent and short-term memory information.
    """
    mem_mgr = web_state.memory_manager or MemoryManager()
    all_memories = mem_mgr.list_memory()
    short_term = mem_mgr.get_short_term_history()

    return MemoryListResponse(
        persistent_count=len(all_memories),
        short_term_count=len(short_term),
        memories=all_memories
    )


@router.post("/memory")
async def store_memory(req: RememberRequest) -> Dict[str, Any]:
    """
    Stores an intentional fact or preference into persistent memory.
    """
    mem_mgr = web_state.memory_manager or MemoryManager()
    record = mem_mgr.remember(req.key, req.value, req.metadata)

    # Publish memory update event
    event_bus.publish(
        event_type="memory_update",
        data={"action": "remember", "key": req.key, "value": req.value}
    )

    return {"status": "success", "record": record}


@router.delete("/memory/{key}")
async def forget_memory(key: str) -> Dict[str, Any]:
    """
    Deletes a fact from persistent memory.
    """
    mem_mgr = web_state.memory_manager or MemoryManager()
    removed = mem_mgr.forget(key)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory key '{key}' not found."
        )

    # Publish memory update event
    event_bus.publish(
        event_type="memory_update",
        data={"action": "forget", "key": key}
    )

    return {"status": "success", "key": key, "removed": removed}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Processes a user text prompt using JarvisCore.
    """
    jarvis_core = web_state.jarvis_core
    if not jarvis_core:
        from app.core import JarvisCore
        jarvis_core = JarvisCore(settings=settings)

    event_bus.publish("user_message", data={"message": req.message})

    # Query JarvisCore
    response_text = await jarvis_core.respond(req.message)

    event_bus.publish("assistant_message", data={"message": response_text})

    return ChatResponse(
        user_text=req.message,
        assistant_response=response_text,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/system", response_model=SystemDiagnosticsResponse)
async def get_system_diagnostics() -> SystemDiagnosticsResponse:
    """
    Gathers host hardware metrics and connectivity diagnostics.
    """
    status_tool = SystemStatusTool()
    sys_metrics = await status_tool.execute()

    ollama_conn = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{settings.llm.api_base}/api/tags")
            ollama_conn = (res.status_code == 200)
    except Exception:
        ollama_conn = False

    return SystemDiagnosticsResponse(
        cpu_load=sys_metrics.get("cpu_load_averages", {"1_min": 0.0, "5_min": 0.0, "15_min": 0.0}),
        memory=sys_metrics.get("memory", {"total_gb": 0.0, "used_gb": 0.0, "percent_used": 0.0}),
        disk=sys_metrics.get("disk", {"total_gb": 0.0, "used_gb": 0.0, "percent_used": 0.0}),
        uptime_seconds=sys_metrics.get("uptime_seconds", 0.0),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        jarvis_version="0.1.0-alpha",
        ollama_connected=ollama_conn
    )


@router.post("/control", response_model=ControlResponse)
async def control_runtime(req: ControlRequest) -> ControlResponse:
    """
    Handles runtime assistant control actions safely.
    """
    action = req.action.lower().strip()

    if action == "stop":
        if web_state.assistant:
            await web_state.assistant.stop()
            event_bus.publish("state_change", data={"state": "SHUTDOWN"})
            return ControlResponse(success=True, message="Assistant stopped successfully.")
        return ControlResponse(success=False, message="Assistant is not running.")

    elif action == "start":
        if web_state.assistant:
            if not web_state.assistant.is_running:
                asyncio.create_task(web_state.assistant.start())
                event_bus.publish("state_change", data={"state": "WAKING"})
                return ControlResponse(success=True, message="Assistant start triggered.")
            return ControlResponse(success=True, message="Assistant is already running.")
        return ControlResponse(success=False, message="No bound assistant instance.")

    elif action == "clear_memory":
        if web_state.memory_manager:
            web_state.memory_manager.clear_memory()
            web_state.memory_manager.clear_short_term()
            event_bus.publish("memory_update", data={"action": "clear"})
            return ControlResponse(success=True, message="Memory cleared successfully.")
        return ControlResponse(success=False, message="No bound memory manager instance.")

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported control action '{action}'."
        )


@router.get("/events")
async def get_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Returns recent live event log feed.
    """
    return event_bus.get_recent_events(limit=limit)
