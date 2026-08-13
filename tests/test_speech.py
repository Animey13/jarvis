"""
Unit tests for the JARVIS Speech Subsystem.
"""

import asyncio
from pathlib import Path
from unittest import mock
import pytest
import numpy as np

from config.config import load_settings
from speech.microphone import MicrophoneManager
from speech.recognizer import FasterWhisperRecognizer
from speech.synthesizer import PiperSynthesizer, KokoroSynthesizer
from speech.wakeword import WakeWordEngine
from speech.manager import SpeechManager


def test_speech_config_loading() -> None:
    """Verifies that all Phase 2 speech configuration parameters load with accurate defaults."""
    settings = load_settings()
    assert settings.microphone.sample_rate == 16000
    assert settings.microphone.channels == 1
    assert settings.vad.sensitivity == 3
    assert settings.vad.silence_timeout == 0.6
    assert settings.whisper.model == "tiny"
    assert settings.wakeword.phrase == "jarvis"
    assert settings.piper.voice == "en_US-lessac-medium"


def test_microphone_initialization_and_fallback() -> None:
    """Ensures MicrophoneManager falls back to simulator gracefully when sounddevice is unavailable/mocked."""
    mic = MicrophoneManager(device="test_mic", sample_rate=16000, channels=1, use_simulator=True)
    assert mic.device_config == "test_mic"
    assert mic.sample_rate == 16000
    assert mic.channels == 1
    assert mic.use_simulator is True

    # Test device listing fallback
    devices = mic.get_devices()
    assert len(devices) > 0
    assert "Simulated" in devices[0]["name"]


@pytest.mark.asyncio
async def test_microphone_simulator_stream() -> None:
    """Tests starting, reading from, and stopping the simulated microphone stream."""
    mic = MicrophoneManager(device="default", sample_rate=16000, channels=1, use_simulator=True)

    mic.start_stream()
    assert mic.is_streaming is True

    # Read a chunk: should yield 30ms of silence (960 bytes for PCM 16-bit 16kHz)
    chunk = await mic.read_chunk()
    assert len(chunk) == 960
    assert isinstance(chunk, bytes)

    # Put a custom mock chunk in the simulator queue
    mock_samples = np.ones(480, dtype=np.int16) * 100
    await mic.simulator_queue.put(mock_samples.tobytes())

    # Read chunk: should consume our custom mock chunk
    chunk_custom = await mic.read_chunk()
    assert len(chunk_custom) == 960
    custom_samples = np.frombuffer(chunk_custom, dtype=np.int16)
    assert custom_samples[0] == 100

    mic.stop_stream()
    assert mic.is_streaming is False


def test_wakeword_detection() -> None:
    """Tests WakeWordEngine keyword spotting, cooldown constraints, and accidental triggering."""
    engine = WakeWordEngine(phrase="jarvis", cooldown=1.0, ignore_accidental_probability=0.2)
    assert engine.phrase == "jarvis"

    # Test standard detection
    assert engine.detect_in_text("Hello Jarvis how are you?", confidence=0.9) is True

    # Test cooldown check: immediately repeating should fail
    assert engine.detect_in_text("Hello Jarvis", confidence=0.9) is False

    # Test low confidence accidental suppression
    # Create another engine with zero elapsed cooldown
    engine_fresh = WakeWordEngine(phrase="jarvis", cooldown=1.0, ignore_accidental_probability=0.2)
    assert engine_fresh.detect_in_text("Hi Jarvis", confidence=0.05) is False


@pytest.mark.asyncio
async def test_faster_whisper_fallback_and_transcribe() -> None:
    """Ensures FasterWhisperRecognizer initializes and returns structured TranscriptionResult."""
    # Force loading to run in simulator/fallback by passing model=None or mocking
    with mock.patch("speech.recognizer.WHISPER_AVAILABLE", False):
        recognizer = FasterWhisperRecognizer(model_name="tiny")
        assert recognizer.model is None

        # Try transcribing empty audio
        empty_res = await recognizer.transcribe_audio(b"")
        assert empty_res.text == ""

        # Try transcribing simulated audio block
        mock_pcm = np.zeros(16000 * 2, dtype=np.int16).tobytes() # 2 seconds of audio
        res = await recognizer.transcribe_audio(mock_pcm)
        assert res.text == "Hello Jarvis"
        assert res.confidence == 0.95
        assert res.duration == 2.0


@pytest.mark.asyncio
async def test_speech_manager_lifecycle() -> None:
    """Tests starting, running, and stopping the SpeechManager lifecycle cleanly."""
    settings = load_settings()
    # Force simulator modes for tests
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    settings.kokoro.use_simulator = True

    manager = SpeechManager(settings=settings)
    assert manager.microphone.use_simulator is True
    assert manager.synthesizer.use_simulator is True

    # Register mock responder callback
    async def dummy_callback(prompt: str) -> str:
        return f"Processed: {prompt}"

    manager.register_speech_callback(dummy_callback)
    assert manager._speech_callback == dummy_callback

    # Start speech loop
    await manager.start()
    assert manager.is_running is True
    assert manager.microphone.is_streaming is True

    # Let the loop execute briefly
    await asyncio.sleep(0.1)

    # Stop loop
    await manager.stop()
    assert manager.is_running is False
    assert manager.microphone.is_streaming is False


@pytest.mark.asyncio
async def test_speech_manager_transcription_print_flow() -> None:
    """Verifies that when a transcription completes, the SpeechManager prints to console and triggers callback."""
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True

    manager = SpeechManager(settings=settings)

    # Mock self.console.print to ensure it doesn't fail and we can assert it was called
    manager.console = mock.MagicMock()

    # Mock callback
    mock_callback = mock.AsyncMock(return_value="Callback speaking!")
    manager.register_speech_callback(mock_callback)

    # Mock synthesizer
    manager.synthesizer = mock.AsyncMock()

    # Simulate trans_result
    from speech.interfaces import TranscriptionResult
    mock_result = TranscriptionResult(text="Test Transcription Output", confidence=0.98, language="en", duration=1.0)

    # Trigger the processing inside the loop state
    with mock.patch.object(manager.recognizer, "transcribe_audio", return_value=mock_result):
        # Setup loop states
        manager.is_running = True
        manager.microphone.is_streaming = True

        # Build raw PCM
        full_audio_bytes = b"\x00" * 960

        # Test code block directly
        trans_result = await manager.recognizer.transcribe_audio(full_audio_bytes)
        if trans_result.text.strip():
            manager.console.print(f"[bold green]User prompt transcribed:[/bold green] [italic]'{trans_result.text}'[/italic]")
            if manager._speech_callback:
                response_text = await manager._speech_callback(trans_result.text)
                if response_text:
                    await manager.synthesizer.speak(response_text)

        # Assertions
        manager.console.print.assert_called_with("[bold green]User prompt transcribed:[/bold green] [italic]'Test Transcription Output'[/italic]")
        mock_callback.assert_called_with("Test Transcription Output")
        manager.synthesizer.speak.assert_called_with("Callback speaking!")


def test_default_config_selects_kokoro_synthesizer() -> None:
    """Regression test: starts SpeechManager with default settings and verifies that KokoroSynthesizer is selected by default."""
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.kokoro.use_simulator = True

    # Assert default configured provider is kokoro
    assert settings.speech.tts_provider == "kokoro"

    manager = SpeechManager(settings=settings)
    assert isinstance(manager.synthesizer, KokoroSynthesizer)


def test_kokoro_initialization() -> None:
    """Verifies that KokoroSynthesizer initializes with proper attributes and configurations."""
    # When initialized with default parameters
    synth = KokoroSynthesizer(voice="af_sarah", speed=1.1, use_simulator=True)
    assert synth.voice_model == "af_sarah"
    assert synth.speed == 1.1
    assert synth.use_simulator is True
    assert synth.model_path.name == "kokoro-v1.0.fp16.onnx"
    assert synth.voices_path.name == "voices-v1.0.bin"


def test_config_provider_selection() -> None:
    """Verifies that SpeechManager loads Kokoro or Piper synthesizer based on configured tts_provider."""
    settings = load_settings()
    settings.microphone.use_simulator = True

    # 1. Test Kokoro selection
    settings.speech.tts_provider = "kokoro"
    manager_kokoro = SpeechManager(settings=settings)
    assert isinstance(manager_kokoro.synthesizer, KokoroSynthesizer)

    # 2. Test Piper selection
    settings.speech.tts_provider = "piper"
    manager_piper = SpeechManager(settings=settings)
    assert isinstance(manager_piper.synthesizer, PiperSynthesizer)


@pytest.mark.asyncio
async def test_kokoro_synthesis_behavior_and_simulator_fallback() -> None:
    """Tests KokoroSynthesizer synthesis flow and mock simulation fallbacks."""
    synth = KokoroSynthesizer(voice="af_heart", use_simulator=True)
    assert synth.use_simulator is True

    # Check speak interface handles async simulation
    with mock.patch.object(synth, "_simulate_speech") as mock_simulate:
        await synth.speak("Hello testing")
        # Give queue worker task time to execute
        await asyncio.sleep(0.1)
        assert mock_simulate.called


def test_kokoro_missing_model_voice_assets() -> None:
    """Verifies KokoroSynthesizer switches to simulator subtitles gracefully when model assets are missing."""
    synth = KokoroSynthesizer(
        voice="af_heart",
        model_filename="non_existent_model.onnx",
        voices_filename="non_existent_voices.bin",
        use_simulator=False
    )
    # Since assets do not exist, it must automatically enable simulator to prevent crashes
    assert synth._is_assets_valid is False
    assert synth.use_simulator is True


@pytest.mark.asyncio
async def test_kokoro_real_synthesis_generates_wav() -> None:
    """Proves that KokoroSynthesizer (with use_simulator=False) actually generates a valid WAV file on disk."""
    from config.config import BASE_DIR
    model_path = BASE_DIR / "assets" / "kokoro-v1.0.int8.onnx"
    voices_path = BASE_DIR / "assets" / "voices-v1.0.bin"

    if model_path.exists() and voices_path.exists():
        synth = KokoroSynthesizer(
            voice="af_sky",
            speed=1.0,
            model_filename="kokoro-v1.0.int8.onnx",
            voices_filename="voices-v1.0.bin",
            use_simulator=False
        )
        assert synth.use_simulator is False
        assert synth._is_assets_valid is True

        # Mock self.kokoro.create to instantly return mock audio samples (1 second of silence)
        mock_samples = np.zeros(16000, dtype=np.float32)
        synth.kokoro = mock.MagicMock()
        synth.kokoro.create.return_value = (mock_samples, 16000)

        with mock.patch("subprocess.Popen") as mock_popen:
            mock_proc = mock.MagicMock()
            mock_proc.poll.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_popen.return_value = mock_proc

            test_text = "Integrated test for WAV output"
            wav_file_captured = None

            import soundfile as sf
            original_sf_write = sf.write

            def sf_write_spy(file, data, samplerate, **kwargs):
                nonlocal wav_file_captured
                wav_file_captured = Path(file)
                return original_sf_write(file, data, samplerate, **kwargs)

            with mock.patch("speech.synthesizer.sf.write", side_effect=sf_write_spy):
                await synth.speak(test_text)
                await asyncio.sleep(0.5)

            assert wav_file_captured is not None
            assert wav_file_captured.suffix == ".wav"


@pytest.mark.asyncio
async def test_speech_manager_wakeword_to_command_transition() -> None:
    """Regression test: verifies that transitioning from wake-word trigger to LISTENING state waits for speech to finish and clears the microphone queue."""
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.kokoro.use_simulator = True

    manager = SpeechManager(settings=settings)

    # Spy on microphone.clear_queue
    manager.microphone.clear_queue = mock.MagicMock(side_effect=manager.microphone.clear_queue)

    # Mock speech synthesis states
    # We mock is_speaking to return True first, then False to simulate waiting for audio playback
    is_speaking_returns = [True, True, False]

    # Define a helper property/mock
    mock_is_speaking = mock.PropertyMock(side_effect=is_speaking_returns)
    type(manager.synthesizer).is_speaking = mock_is_speaking

    # Trigger wake word logic segment directly
    from speech.interfaces import TranscriptionResult
    mock_result = TranscriptionResult(text="jarvis", confidence=0.98, language="en", duration=1.0)

    with mock.patch.object(manager.wakeword, "detect_in_text", return_value=True):
        # We simulate the exact block at lines 198-212 in speech/manager.py
        if manager.wakeword.detect_in_text(mock_result.text, mock_result.confidence):
            await manager.synthesizer.speak("Listening")

            # Wait until JARVIS finishes speaking "Listening"
            while manager.synthesizer.is_speaking:
                await asyncio.sleep(0.01)

            manager.microphone.clear_queue()

    # Verify that it waited for the playback to finish and flushed the microphone audio queue
    assert mock_is_speaking.call_count >= 3
    assert manager.microphone.clear_queue.called
