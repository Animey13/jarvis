"""
Focused regression tests for the JARVIS Microphone format and capture boundary.
Verifies that MicrophoneManager correctly handles float32 captures, default device config,
and safely transforms arrays to the int16 format expected by Whisper/webrtcvad.
"""

from unittest import mock
import pytest
import numpy as np

import speech.microphone as mic_module
from speech.microphone import MicrophoneManager

# Set up mock sounddevice on the microphone module directly to bypass module caching
mock_sd = mock.MagicMock()
mock_sd.query_devices.return_value = [
    {"name": "default", "max_input_channels": 2, "default_samplerate": 44100.0}
]
mock_sd.default.device = [0, 0]


def test_microphone_default_device_selection() -> None:
    """
    Verifies that choosing "default" device config uses 'default' explicitly,
    bypassing physical index checks to utilize ALSA's system defaults.
    """
    with mock.patch.object(mic_module, "sd", mock_sd):
        with mock.patch.object(mic_module, "SOUNDDEVICE_AVAILABLE", True):
            mic = MicrophoneManager(device="default", sample_rate=16000, channels=1, use_simulator=False)
            assert mic.use_simulator is False
            assert mic._physical_device_idx == "default"
            assert mic._device_name == "default"
            assert mic._actual_sample_rate == 16000


@pytest.mark.asyncio
async def test_float32_to_int16_conversion_flow() -> None:
    """
    Verifies that the capture path's audio callback correctly converts
    normalized float32 audio to signed int16 PCM bytes.
    """
    with mock.patch.object(mic_module, "sd", mock_sd):
        with mock.patch.object(mic_module, "SOUNDDEVICE_AVAILABLE", True):
            mic = MicrophoneManager(device="default", sample_rate=16000, channels=1, use_simulator=False)

            # Simulate sounddevice input stream callback data
            # Create float32 mock input (mono channel, values alternating between 0.5 and -0.5)
            mock_float32_indata = np.array([[0.5], [-0.5], [0.0]], dtype=np.float32)

            # Start stream which instantiates InputStream
            mic.start_stream()
            assert mock_sd.InputStream.called

            # Extract the callback passed to InputStream
            args, kwargs = mock_sd.InputStream.call_args
            captured_callback = kwargs.get("callback")
            assert captured_callback is not None

            # Call the callback with our mock float32 data
            captured_callback(mock_float32_indata, len(mock_float32_indata), None, None)

            # Read the raw bytes from the microphone queue
            chunk_bytes = await mic._audio_queue.get()
            assert isinstance(chunk_bytes, bytes)

            # Convert bytes back to int16 numpy array to verify conversion values
            converted_samples = np.frombuffer(chunk_bytes, dtype=np.int16)

            # 0.5 * 32768.0 = 16384
            # -0.5 * 32768.0 = -16384
            # 0.0 * 32768.0 = 0
            assert len(converted_samples) == 3
            assert converted_samples[0] == 16384
            assert converted_samples[1] == -16384
            assert converted_samples[2] == 0

            # Clean up
            mic.stop_stream()
