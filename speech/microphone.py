"""
JARVIS Microphone Manager Module.

Implements the AudioInput interface to manage physical or simulated microphone capture.
Supports automatic fallback to a simulated input queue when PortAudio is unavailable.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import numpy as np

from speech.interfaces import AudioInput

logger = logging.getLogger(__name__)

# Try to import sounddevice safely, falling back to simulator mode if missing
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError) as e:
    logger.warning("sounddevice or PortAudio library not available. Falling back to simulated microphone. Error: %s", e)
    SOUNDDEVICE_AVAILABLE = False


class MicrophoneManager(AudioInput):
    """
    Manages physical audio capture using sounddevice/PortAudio, or falls back to
    yielding simulated PCM 16-bit audio when hardware/libraries are absent.
    """

    def __init__(
        self,
        device: str = "default",
        sample_rate: int = 16000,
        channels: int = 1,
        use_simulator: bool = False
    ) -> None:
        """
        Initializes the MicrophoneManager.

        Args:
            device: Target audio input device name or index.
            sample_rate: Configuration sample rate in Hz (defaults to 16000 for Whisper).
            channels: Configuration input audio channels (defaults to 1).
            use_simulator: Force the microphone manager to run in simulator mode.
        """
        self.device_config: str = device
        self.sample_rate: int = sample_rate
        self.channels: int = channels
        self.use_simulator: bool = use_simulator or not SOUNDDEVICE_AVAILABLE
        self.is_streaming: bool = False

        # Asynchronous Queue for captured audio frames
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stream: Optional[Any] = None

        # Simulator attributes
        self.simulator_queue: asyncio.Queue[bytes] = asyncio.Queue()

        # Cached device list
        self._devices_cache: List[Dict[str, Any]] = []

        logger.info(
            "MicrophoneManager initialized (Device: %s, SR: %d, Channels: %d, Simulator Mode: %s)",
            self.device_config, self.sample_rate, self.channels, self.use_simulator
        )

    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Retrieves a list of available sound input devices from the OS.

        Returns:
            List[Dict[str, Any]]: List of device maps, or mock devices if offline/missing.
        """
        if self.use_simulator or not SOUNDDEVICE_AVAILABLE:
            return [{"name": "Simulated Virtual Microphone", "index": 0, "max_input_channels": 1}]

        if self._devices_cache:
            return self._devices_cache

        try:
            device_list: List[Dict[str, Any]] = []
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    device_list.append({
                        "name": dev.get("name", f"Device {idx}"),
                        "index": idx,
                        "max_input_channels": dev.get("max_input_channels", 1),
                        "default_samplerate": dev.get("default_samplerate", 16000.0)
                    })
            self._devices_cache = device_list
            return device_list
        except Exception as e:
            logger.error("Failed to query sound devices: %s. Falling back to simulation lists.", e)
            return [{"name": "Simulated Virtual Microphone (Query Fallback)", "index": 0, "max_input_channels": 1}]

    def _get_device_index(self) -> Optional[Any]:
        """
        Resolves the configured device name to a physical device index.
        """
        if self.device_config == "default":
            return None

        try:
            # Check if device configuration is specified as an integer index
            return int(self.device_config)
        except ValueError:
            pass

        devices = self.get_devices()
        for dev in devices:
            if self.device_config.lower() in dev["name"].lower():
                return dev["index"]

        logger.warning("Configured device '%s' not found. Falling back to default device.", self.device_config)
        return None

    def start_stream(self) -> None:
        """
        Starts non-blocking audio capture. Registers streaming handlers on hardware
        or triggers internal simulation loops.
        """
        if self.is_streaming:
            logger.warning("Audio capture stream already running.")
            return

        self._loop = asyncio.get_event_loop()
        self.is_streaming = True

        # Flush queues
        while not self._audio_queue.empty():
            self._audio_queue.get_nowait()

        if self.use_simulator:
            logger.info("Starting virtual microphone simulation stream.")
            return

        # Initialize physical sounddevice stream
        device_idx = self._get_device_index()
        logger.info("Opening physical input stream on device: %s", device_idx if device_idx is not None else "Default")

        def audio_callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
            """Callback from PortAudio running on separate OS thread."""
            if status:
                logger.warning("PortAudio status warning: %s", status)

            # Convert NumPy float32 or int16 data to raw 16-bit PCM bytes
            raw_bytes = indata.tobytes()
            if self._loop and self.is_streaming:
                self._loop.call_soon_threadsafe(self._audio_queue.put_nowait, raw_bytes)

        try:
            self._stream = sd.InputStream(
                device=device_idx,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=audio_callback,
                blocksize=480 # 30ms frames for 16000Hz (16000 * 0.03 = 480 samples)
            )
            self._stream.start()
            logger.info("Microphone input stream started successfully.")
        except Exception as e:
            logger.error("Failed to open physical audio stream: %s. Switching to virtual simulation.", e)
            self.use_simulator = True
            # Re-call stream start in simulation mode
            self.is_streaming = False
            self.start_stream()

    def stop_stream(self) -> None:
        """
        Stops audio capture and releases hardware resources.
        """
        if not self.is_streaming:
            return

        logger.info("Stopping microphone capture stream.")
        self.is_streaming = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error("Error closing physical audio stream: %s", e)
            finally:
                self._stream = None

    async def read_chunk(self) -> bytes:
        """
        Reads a 30ms chunk of PCM 16-bit mono audio.

        Returns:
            bytes: Raw PCM bytes.
        """
        if not self.is_streaming:
            raise RuntimeError("Microphone stream is not running. Call start_stream() first.")

        if self.use_simulator:
            # Simulator mode: Check if simulated speech data is available in queue
            try:
                return self.simulator_queue.get_nowait()
            except asyncio.QueueEmpty:
                # Fallback to generating 30ms of simulated background comfort noise (silence)
                # 30ms chunk at 16000Hz = 480 samples * 2 bytes/sample = 960 bytes
                await asyncio.sleep(0.03)
                samples = np.zeros(480, dtype=np.int16)
                return samples.tobytes()

        # Physical mode: Wait for chunk from sounddevice stream queue
        try:
            # 30ms chunks arrive fast, wait up to 0.5s before assuming stream error
            return await asyncio.wait_for(self._audio_queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            logger.warning("Audio read timeout. Attempting stream recovery...")
            self._recover_stream()
            # Return silent fallback chunk on timeout
            return np.zeros(480, dtype=np.int16).tobytes()

    def _recover_stream(self) -> None:
        """
        Attempts to recover and rebuild the stream if hardware disconnects.
        """
        logger.info("Triggering microphone stream recovery flow...")
        try:
            self.stop_stream()
            await_loop = asyncio.get_event_loop()
            # Give OS time to settle, then restart
            await_loop.call_later(0.1, self.start_stream)
        except Exception as e:
            logger.error("Graceful recovery failed: %s. Falling back to simulator mode.", e)
            self.use_simulator = True
            self.start_stream()
