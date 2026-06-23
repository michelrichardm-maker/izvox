"""Tests pour AudioManager (mockés - pas de matériel requis)."""

from unittest.mock import MagicMock, patch

import pytest

from src.audio_manager import AudioManager, DeviceInfo
from src.config import AudioConfig
from src.exceptions import AudioDeviceNotFoundError


@pytest.fixture
def mock_pyaudio():
    """Simule pyaudiowpatch."""
    with patch("src.audio_manager._import_pyaudio") as import_pa:
        pa_module = MagicMock()
        pa_module.paInt16 = 8
        pa_module.paWASAPI = 13

        pa_instance = MagicMock()
        pa_instance.get_device_count.return_value = 3
        pa_instance.get_device_info_by_index.side_effect = [
            {
                "index": 0,
                "name": "Microphone (Realtek)",
                "maxInputChannels": 1,
                "maxOutputChannels": 0,
                "defaultSampleRate": 16000,
                "hostApi": 0,
            },
            {
                "index": 1,
                "name": "CABLE Input (VB-Audio Virtual Cable)",
                "maxInputChannels": 0,
                "maxOutputChannels": 2,
                "defaultSampleRate": 44100,
                "hostApi": 0,
            },
            {
                "index": 2,
                "name": "Haut-parleurs (Realtek)",
                "maxInputChannels": 0,
                "maxOutputChannels": 2,
                "defaultSampleRate": 44100,
                "hostApi": 0,
            },
        ]
        pa_module.PyAudio.return_value = pa_instance
        import_pa.return_value = pa_module
        yield pa_module, pa_instance


def test_list_devices(mock_pyaudio):
    manager = AudioManager()
    devices = manager.list_devices()
    assert len(devices) == 3
    assert devices[0].is_input is True
    assert devices[1].is_output is True


def test_list_input_devices_only(mock_pyaudio):
    manager = AudioManager()
    inputs = manager.list_devices(input_only=True)
    assert all(d.is_input for d in inputs)
    assert len(inputs) == 1


def test_find_device_by_pattern(mock_pyaudio):
    manager = AudioManager()
    device = manager.find_device("CABLE Input", output_only=True)
    assert "CABLE Input" in device.name


def test_find_device_not_found(mock_pyaudio):
    manager = AudioManager()
    with pytest.raises(AudioDeviceNotFoundError):
        manager.find_device("DeviceThatDoesNotExist")


def test_device_info_dataclass():
    device = DeviceInfo(
        index=0,
        name="Test",
        max_input_channels=1,
        max_output_channels=0,
        default_sample_rate=16000,
        is_input=True,
        is_output=False,
    )
    assert device.is_input is True
    assert device.is_loopback is False


def test_audio_config_compatible_with_manager(mock_pyaudio):
    """AudioConfig est bien interprété par open_input_stream."""
    pa_module, pa_instance = mock_pyaudio
    pa_instance.open.return_value = MagicMock()

    manager = AudioManager()
    cfg = AudioConfig(sample_rate=16000, channels=1, chunk_size=512)
    manager.open_input_stream(
        config=cfg, device_pattern="Microphone", stream_id="test"
    )
    pa_instance.open.assert_called_once()
    kwargs = pa_instance.open.call_args.kwargs
    assert kwargs["rate"] == 16000
    assert kwargs["channels"] == 1
    assert kwargs["frames_per_buffer"] == 512
