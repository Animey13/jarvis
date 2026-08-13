"""
JARVIS Microphone Manager Module.

Implements the AudioInput interface to manage physical or simulated microphone capture.
Provides automatic device negotiation, sample rate resampling, and robust fallback logic.
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
        self.is_streaming: bool = False

        # Determine if sounddevice is available and has recording devices
        self.has_physical_devices = False
        self._physical_device_idx: Optional[int] = None
        self._device_name: str = "Simulated Virtual Microphone"
        self._actual_sample_rate: int = sample_rate

        if SOUNDDEVICE_AVAILABLE:
            try:
                devices = sd.query_devices()
                input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
                if len(input_devices) > 0:
                    self.has_physical_devices = True
            except Exception as e:
                logger.warning("Failed to query sounddevice devices: %s", e)
                self.has_physical_devices = False

        # Simulator Gating Rules:
        # Simulator should only activate if:
        # - no recording device exists
        # - user explicitly enables simulator
        # - sounddevice initialization fails entirely
        self.use_simulator: bool = use_simulator or not self.has_physical_devices

        # Auto select the input device and default parameters
        if not self.use_simulator:
            self._select_input_device()

        # Asynchronous Queue for captured audio frames
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stream: Optional[Any] = None

        # Simulator attributes
        self.simulator_queue: asyncio.Queue[bytes] = asyncio.Queue()

        # Startup logging as requested:
        # Input Device:
        # Sample Rate:
        # Channels:
        # Backend:
        # Simulation:
        backend_str = "PortAudio / sounddevice" if not self.use_simulator else "Simulated"
        simulation_str = "Enabled" if self.use_simulator else "Disabled"
        logger.info("========================================")
        logger.info("JARVIS Microphone Subsystem initialized:")
        logger.info("  Input Device: %s", self._device_name)
        logger.info("  Sample Rate:  %dHz (Actual: %dHz)", self.sample_rate, self._actual_sample_rate)
        logger.info("  Channels:     %d", self.channels)
        logger.info("  Backend:      %s", backend_str)
        logger.info("  Simulation:   %s", simulation_str)
        logger.info("========================================")

    def _select_input_device(self) -> None:
        """
        Automatically selects the default or first available physical input device.
        """
        try:
            devices = sd.query_devices()

            # Resolve the default input device
            default_input_idx = sd.default.device[0]

            # Find all devices with input channels
            input_devices = [d for idx, d in enumerate(devices) if d.get("max_input_channels", 0) > 0]

            if not input_devices:
                self.use_simulator = True
                self._device_name = "Simulated Virtual Microphone"
                return

            selected_idx: Optional[int] = None

            # Scenario A: Device is explicit index
            try:
                idx = int(self.device_config)
                if idx < len(devices) and devices[idx].get("max_input_channels", 0) > 0:
                    selected_idx = idx
            except ValueError:
                pass

            # Scenario B: Device is string name search
            if selected_idx is None and self.device_config != "default":
                for idx, dev in enumerate(devices):
                    if dev.get("max_input_channels", 0) > 0 and self.device_config.lower() in dev.get("name", "").lower():
                        selected_idx = idx
                        break

            # Scenario C: Use Default recording device index
            if selected_idx is None and default_input_idx is not None and default_input_idx >= 0:
                selected_idx = default_input_idx

            # Scenario D: Fallback to first available input device
            if selected_idx is None:
                for idx, dev in enumerate(devices):
                    if dev.get("max_input_channels", 0) > 0:
                        selected_idx = idx
                        break

            if selected_idx is not None:
                self._physical_device_idx = selected_idx
                dev_info = devices[selected_idx]
                self._device_name = dev_info.get("name", f"Device {selected_idx}")
                self._actual_sample_rate = int(dev_info.get("default_samplerate", self.sample_rate))
                logger.info("Selected input device '%s' (Index: %d) as recording source.", self._device_name, selected_idx)
            else:
                self.use_simulator = True
                self._device_name = "Simulated Virtual Microphone"

        except Exception as e:
            logger.error("Error selecting input device: %s. Falling back to simulator.", e)
            self.use_simulator = True
            self._device_name = "Simulated Virtual Microphone"

    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Retrieves a list of available sound input devices from the OS.

        Returns:
            List[Dict[str, Any]]: List of device maps, or mock devices if offline/missing.
        """
        if self.use_simulator or not SOUNDDEVICE_AVAILABLE:
            return [{"name": "Simulated Virtual Microphone", "index": 0, "max_input_channels": 1}]

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
            return device_list
        except Exception as e:
            logger.error("Failed to query sound devices: %s. Falling back to simulation lists.", e)
            return [{"name": "Simulated Virtual Microphone (Query Fallback)", "index": 0, "max_input_channels": 1}]

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
        logger.info("Opening physical input stream on device: %s (Index: %s)", self._device_name, self._physical_device_idx)

        # Helper to downsample audio arrays to target 16000Hz if device defaults differ
        def resample_audio(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
            if src_rate == dst_rate:
                return samples
            num_samples_dst = int(len(samples) * (dst_rate / src_rate))
            return np.interp(
                np.linspace(0, len(samples), num_samples_dst, endpoint=False),
                np.arange(len(samples)),
                samples
            ).astype(np.int16)

        def audio_callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
            """Callback from PortAudio running on separate OS thread."""
            if status:
                logger.warning("PortAudio status warning: %s", status)

            # Convert captured buffer to int16 samples and resample if necessary
            samples = indata[:, 0]  # Take channel 0

            if self._actual_sample_rate != self.sample_rate:
                samples = resample_audio(samples, self._actual_sample_rate, self.sample_rate)

            # Ensure we deliver 30ms-equivalent blocks if possible, or directly deliver
            raw_bytes = samples.tobytes()
            if self._loop and self.is_streaming:
                self._loop.call_soon_threadsafe(self._audio_queue.put_nowait, raw_bytes)

        # Device parameter negotiation falling back to defaults if configured target fails
        negotiation_rates = [self.sample_rate, self._actual_sample_rate, 44100, 48000, 16000]
        opened_successfully = False

        for rate in negotiation_rates:
            try:
                # Calculate appropriate blocksize for 30ms at selected sample rate
                # 30ms at Rate = Rate * 0.03
                block_size = int(rate * 0.03)
                logger.info("Attempting to open input stream (Rate: %dHz, Device Index: %s, Block size: %d)", rate, self._physical_device_idx, block_size)

                self._stream = sd.InputStream(
                    device=self._physical_device_idx,
                    samplerate=rate,
                    channels=self.channels,
                    dtype="int16",
                    callback=audio_callback,
                    blocksize=block_size
                )
                self._stream.start()
                self._actual_sample_rate = rate
                opened_successfully = True
                logger.info("Microphone input stream started successfully at %dHz.", rate)
                break
            except Exception as e:
                logger.warning("Failed to open physical stream with sample rate %dHz: %s", rate, e)
                continue

        if not opened_successfully:
            # If we couldn't open any stream even though we have devices, raise RuntimeError
            # (Simulator should only activate if sounddevice initialization fails entirely,
            # meaning we can't load the binary or find devices. Since devices DO exist,
            # we should raise an initialization error rather than silently masking it!)
            raise RuntimeError(f"Failed to initialize physical microphone input stream on device {self._device_name}.")

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

    def clear_queue(self) -> None:
        """
        Clears any pending captured audio data from the input stream.
        """
        logger.debug("Flushing microphone audio queue.")
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def _recover_stream(self) -> None:
        """
        Attempts to recover and rebuild the stream if hardware disconnects.
        """
        logger.info("Triggering microphone stream recovery flow...")
        try:
            self.stop_stream()
            await_loop = asyncio.get_event_loop()
            await_loop.call_later(0.1, self.start_stream)
        except Exception as e:
            logger.error("Graceful recovery failed: %s. Falling back to simulator mode.", e)
            self.use_simulator = True
            self.start_stream()
