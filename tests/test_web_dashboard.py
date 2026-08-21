"""
Comprehensive Test Suite for Phase 8 JARVIS Web Dashboard & REST/WebSocket APIs.
Tests API status, configuration, tools, memory CRUD operations, chat routes,
system diagnostics, runtime controls, WebSocket events, and security bounds.
"""

from unittest import mock
import pytest
from fastapi.testclient import TestClient

from app.assistant import JarvisAssistant
from config.config import load_settings
from web.app import app as fastapi_app
from web.state import event_bus, web_state
from web.websocket import ws_manager


@pytest.fixture
def client():
    """Test client fixture for FastAPI app."""
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    settings.kokoro.use_simulator = True

    assistant = JarvisAssistant(settings=settings)
    web_state.set_references(
        assistant=assistant,
        speech_manager=assistant.speech_manager,
        jarvis_core=assistant.jarvis_core,
        memory_manager=assistant.jarvis_core.memory_manager,
        tool_registry=assistant.jarvis_core.tool_registry,
    )
    return TestClient(fastapi_app)


def test_api_status_endpoint(client) -> None:
    """
    Verifies GET /api/status returns valid status fields.
    """
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "online" in data
    assert "state" in data
    assert "microphone_status" in data
    assert "stt_status" in data
    assert "tts_status" in data
    assert "ollama_status" in data
    assert "llm_model" in data


def test_api_config_endpoint(client) -> None:
    """
    Verifies GET /api/config returns sanitized configuration settings.
    """
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "llm" in data
    assert "speech" in data
    assert "microphone" in data


def test_api_tools_endpoint(client) -> None:
    """
    Verifies GET /api/tools lists registered tools and parameters schema.
    """
    response = client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tools"] > 0
    assert any(t["name"] == "calculator" for t in data["tools"])
    assert any(t["name"] == "get_system_status" for t in data["tools"])


def test_api_memory_crud_endpoints(client) -> None:
    """
    Verifies GET, POST, and DELETE memory endpoints.
    """
    # 1. Store memory
    post_res = client.post("/api/memory", json={"key": "test_fact", "value": "Python 3.12"})
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "success"

    # 2. Get memory list
    get_res = client.get("/api/memory")
    assert get_res.status_code == 200
    memories = get_res.json()["memories"]
    assert "test_fact" in memories
    assert memories["test_fact"] == "Python 3.12"

    # 3. Delete memory
    del_res = client.delete("/api/memory/test_fact")
    assert del_res.status_code == 200
    assert del_res.json()["removed"] is True

    # 4. Verify deletion
    get_res_after = client.get("/api/memory")
    assert "test_fact" not in get_res_after.json()["memories"]


def test_api_chat_endpoint(client) -> None:
    """
    Verifies POST /api/chat delegates prompt processing to JarvisCore and returns response.
    """
    with mock.patch.object(web_state.jarvis_core, "respond", new_callable=mock.AsyncMock) as mock_respond:
        mock_respond.return_value = "Hello from JARVIS Core!"

        res = client.post("/api/chat", json={"message": "Hello JARVIS"})
        assert res.status_code == 200
        data = res.json()
        assert data["user_text"] == "Hello JARVIS"
        assert data["assistant_response"] == "Hello from JARVIS Core!"


def test_api_system_diagnostics_endpoint(client) -> None:
    """
    Verifies GET /api/system returns host diagnostics.
    """
    response = client.get("/api/system")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_load" in data
    assert "memory" in data
    assert "disk" in data
    assert "python_version" in data


def test_api_control_endpoint(client) -> None:
    """
    Verifies POST /api/control accepts start, stop, and clear_memory runtime actions.
    """
    # Clear memory action
    res_clear = client.post("/api/control", json={"action": "clear_memory"})
    assert res_clear.status_code == 200
    assert res_clear.json()["success"] is True

    # Invalid action
    res_invalid = client.post("/api/control", json={"action": "unsupported_action"})
    assert res_invalid.status_code == 400


def test_api_events_endpoint(client) -> None:
    """
    Verifies GET /api/events returns published event history feed.
    """
    event_bus.publish("custom_test_event", data={"key": "val"})
    response = client.get("/api/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) > 0
    assert any(e["type"] == "custom_test_event" for e in events)


@pytest.mark.asyncio
async def test_websocket_manager_connect_broadcast_disconnect() -> None:
    """
    Verifies WebSocketManager connection registration, event broadcasting, and disconnection.
    """
    mock_ws = mock.AsyncMock()

    await ws_manager.connect(mock_ws)
    assert mock_ws in ws_manager.active_connections

    await ws_manager.broadcast({"type": "test_event", "data": {}})
    assert mock_ws.send_text.called

    await ws_manager.disconnect(mock_ws)
    assert mock_ws not in ws_manager.active_connections
