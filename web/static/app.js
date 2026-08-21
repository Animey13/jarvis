/**
 * JARVIS Web Dashboard Client Application Logic.
 * Pure Vanilla JavaScript managing WebSocket event streams, REST API updates,
 * real-time state visualization, conversation UI, and system diagnostics.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Element References
  const wsStatusDot = document.getElementById('ws-dot');
  const wsStatusText = document.getElementById('ws-status-text');
  const appStatusDot = document.getElementById('app-dot');
  const appStatusText = document.getElementById('app-status-text');

  const currentStateTag = document.getElementById('current-state-tag');
  const waveBox = document.getElementById('wave-box');
  const micStatus = document.getElementById('mic-status');
  const sttStatus = document.getElementById('stt-status');
  const ttsStatus = document.getElementById('tts-status');
  const ollamaStatus = document.getElementById('ollama-status');

  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');

  const eventsLog = document.getElementById('events-log');
  const clearEventsBtn = document.getElementById('clear-events-btn');

  const toolsCount = document.getElementById('tools-count');
  const toolsContainer = document.getElementById('tools-container');

  const memoryCount = document.getElementById('memory-count');
  const memoryForm = document.getElementById('memory-form');
  const memKeyInput = document.getElementById('mem-key');
  const memValInput = document.getElementById('mem-val');
  const memoryItems = document.getElementById('memory-items');

  const cpuVal = document.getElementById('cpu-val');
  const cpuBar = document.getElementById('cpu-bar');
  const ramVal = document.getElementById('ram-val');
  const ramBar = document.getElementById('ram-bar');
  const diskVal = document.getElementById('disk-val');
  const diskBar = document.getElementById('disk-bar');
  const uptimeText = document.getElementById('uptime-text');
  const pythonVer = document.getElementById('python-ver');
  const jarvisVer = document.getElementById('jarvis-ver');

  const btnStart = document.getElementById('btn-start');
  const btnStop = document.getElementById('btn-stop');

  let ws = null;

  // -------------------------------------------------------------------------
  // 1. WEBSOCKET REAL-TIME EVENT STREAM
  // -------------------------------------------------------------------------
  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || '127.0.0.1:8000';
    const wsUrl = `${protocol}//${host}/ws`;

    wsStatusText.textContent = 'Connecting...';

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      wsStatusDot.className = 'status-dot online';
      wsStatusText.textContent = 'WS Connected';
      appendEvent({ type: 'system', data: { message: 'WebSocket connection established.' } });
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleWebSocketEvent(payload);
      } catch (e) {
        console.error('Failed to parse WebSocket JSON:', e);
      }
    };

    ws.onclose = () => {
      wsStatusDot.className = 'status-dot offline';
      wsStatusText.textContent = 'WS Disconnected';
      setTimeout(connectWebSocket, 3000); // Auto reconnect
    };

    ws.onerror = (err) => {
      console.error('WebSocket Error:', err);
    };
  }

  function handleWebSocketEvent(event) {
    appendEvent(event);

    switch (event.type) {
      case 'state_change':
        if (event.data && event.data.state) {
          updateStateVisualizer(event.data.state);
        }
        break;
      case 'user_message':
        if (event.data && event.data.message) {
          appendChatMessage('user', event.data.message);
        }
        break;
      case 'assistant_message':
        if (event.data && event.data.message) {
          appendChatMessage('assistant', event.data.message);
        }
        break;
      case 'memory_update':
        fetchMemory();
        break;
      case 'tool_complete':
        fetchTools();
        break;
      default:
        break;
    }
  }

  function appendEvent(event) {
    const item = document.createElement('div');
    item.className = `event-item ${event.type || ''}`;
    const timeStr = new Date().toLocaleTimeString();
    const dataStr = JSON.stringify(event.data || {});
    item.textContent = `[${timeStr}] ${event.type.toUpperCase()}: ${dataStr}`;
    eventsLog.appendChild(item);
    eventsLog.scrollTop = eventsLog.scrollHeight;
  }

  clearEventsBtn.addEventListener('click', () => {
    eventsLog.innerHTML = '';
  });

  // -------------------------------------------------------------------------
  // 2. STATE VISUALIZER UPDATES
  // -------------------------------------------------------------------------
  function updateStateVisualizer(stateName) {
    currentStateTag.textContent = stateName;

    if (['LISTENING', 'TRANSCRIBING', 'THINKING', 'SPEAKING'].includes(stateName)) {
      waveBox.classList.add('active');
    } else {
      waveBox.classList.remove('active');
    }

    if (stateName === 'SPEAKING') {
      currentStateTag.style.background = '#10b981';
    } else if (stateName === 'LISTENING') {
      currentStateTag.style.background = '#00f2fe';
      currentStateTag.style.color = '#000';
    } else if (stateName === 'THINKING') {
      currentStateTag.style.background = '#8b5cf6';
    } else if (stateName === 'INTERRUPTED') {
      currentStateTag.style.background = '#ef4444';
    } else {
      currentStateTag.style.background = '#0088a8';
      currentStateTag.style.color = '#fff';
    }
  }

  // -------------------------------------------------------------------------
  // 3. CONVERSATION CHAT UI
  // -------------------------------------------------------------------------
  function appendChatMessage(role, text) {
    const turn = document.createElement('div');
    turn.className = `chat-turn ${role}`;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.textContent = text;
    turn.appendChild(bubble);
    chatMessages.appendChild(turn);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;

    chatInput.value = '';
    appendChatMessage('user', msg);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();
      if (data.assistant_response) {
        appendChatMessage('assistant', data.assistant_response);
      }
    } catch (err) {
      console.error('Chat API Error:', err);
      appendChatMessage('system', 'Error sending chat message.');
    }
  });

  // -------------------------------------------------------------------------
  // 4. MEMORY PANEL OPERATIONS
  // -------------------------------------------------------------------------
  async function fetchMemory() {
    try {
      const res = await fetch('/api/memory');
      const data = await res.json();

      memoryCount.textContent = data.persistent_count;
      memoryItems.innerHTML = '';

      const memories = data.memories || {};
      const keys = Object.keys(memories);

      if (keys.length === 0) {
        memoryItems.innerHTML = '<div style="color: var(--text-muted); font-size: 0.75rem;">No persistent memories saved.</div>';
        return;
      }

      keys.forEach((k) => {
        const val = memories[k];
        const card = document.createElement('div');
        card.className = 'mem-card';
        card.innerHTML = `
          <div><strong>${k}:</strong> ${val}</div>
          <button class="btn-sm danger" data-key="${k}">Forget</button>
        `;
        card.querySelector('button').addEventListener('click', () => deleteMemory(k));
        memoryItems.appendChild(card);
      });
    } catch (err) {
      console.error('Fetch Memory Error:', err);
    }
  }

  memoryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const k = memKeyInput.value.trim();
    const v = memValInput.value.trim();
    if (!k || !v) return;

    try {
      await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: k, value: v })
      });
      memKeyInput.value = '';
      memValInput.value = '';
      fetchMemory();
    } catch (err) {
      console.error('Store Memory Error:', err);
    }
  });

  async function deleteMemory(key) {
    try {
      await fetch(`/api/memory/${encodeURIComponent(key)}`, {
        method: 'DELETE'
      });
      fetchMemory();
    } catch (err) {
      console.error('Delete Memory Error:', err);
    }
  }

  // -------------------------------------------------------------------------
  // 5. TOOLS PANEL
  // -------------------------------------------------------------------------
  async function fetchTools() {
    try {
      const res = await fetch('/api/tools');
      const data = await res.json();

      toolsCount.textContent = data.total_tools;
      toolsContainer.innerHTML = '';

      (data.tools || []).forEach((t) => {
        const card = document.createElement('div');
        card.className = 'tool-card';
        card.innerHTML = `
          <div>
            <strong>${t.name}</strong>
            <div style="color: var(--text-muted); font-size: 0.7rem;">${t.description}</div>
          </div>
        `;
        toolsContainer.appendChild(card);
      });
    } catch (err) {
      console.error('Fetch Tools Error:', err);
    }
  }

  // -------------------------------------------------------------------------
  // 6. SYSTEM DIAGNOSTICS & STATUS POLLING
  // -------------------------------------------------------------------------
  async function fetchStatusAndDiagnostics() {
    try {
      const [statusRes, diagRes] = await Promise.all([
        fetch('/api/status'),
        fetch('/api/system')
      ]);

      const statusData = await statusRes.json();
      const diagData = await diagRes.json();

      // Update Top Status Badges
      if (statusData.online) {
        appStatusDot.className = 'status-dot online';
        appStatusText.textContent = 'Online';
      } else {
        appStatusDot.className = 'status-dot offline';
        appStatusText.textContent = 'Offline';
      }

      updateStateVisualizer(statusData.state);

      micStatus.textContent = statusData.microphone_status;
      sttStatus.textContent = statusData.stt_status;
      ttsStatus.textContent = statusData.tts_status;
      ollamaStatus.textContent = statusData.ollama_status;

      // Update System Gauges
      const cpu = diagData.cpu_load ? diagData.cpu_load['1_min'] || 0 : 0;
      const ram = diagData.memory ? diagData.memory.percent_used || 0 : 0;
      const disk = diagData.disk ? diagData.disk.percent_used || 0 : 0;

      cpuVal.textContent = `${cpu}%`;
      cpuBar.style.width = `${Math.min(cpu * 10, 100)}%`;

      ramVal.textContent = `${ram}%`;
      ramBar.style.width = `${ram}%`;

      diskVal.textContent = `${disk}%`;
      diskBar.style.width = `${disk}%`;

      uptimeText.textContent = `${Math.round(diagData.uptime_seconds)}s`;
      pythonVer.textContent = diagData.python_version;
      jarvisVer.textContent = diagData.jarvis_version;

    } catch (err) {
      console.error('Diagnostics Polling Error:', err);
    }
  }

  // -------------------------------------------------------------------------
  // 7. RUNTIME CONTROLS
  // -------------------------------------------------------------------------
  btnStart.addEventListener('click', async () => {
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'start' })
      });
      fetchStatusAndDiagnostics();
    } catch (err) {
      console.error('Start Error:', err);
    }
  });

  btnStop.addEventListener('click', async () => {
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'stop' })
      });
      fetchStatusAndDiagnostics();
    } catch (err) {
      console.error('Stop Error:', err);
    }
  });

  // -------------------------------------------------------------------------
  // INITIALIZATION & POLLING LOOPS
  // -------------------------------------------------------------------------
  connectWebSocket();
  fetchTools();
  fetchMemory();
  fetchStatusAndDiagnostics();

  // Poll system metrics every 5 seconds
  setInterval(fetchStatusAndDiagnostics, 5000);
});
