"""
Gestionnaire audio avec support WASAPI (Windows).

Gère la capture microphone, loopback, et sortie vers VB-Cable.
Utilise PyAudioWPatch pour le support natif WASAPI loopback sous Windows.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .config import AudioConfig
from .exceptions import AudioDeviceNotFoundError, AudioStreamError

if TYPE_CHECKING:
    import pyaudiowpatch as pyaudio


def _import_pyaudio():
    """Import paresseux de pyaudiowpatch (Windows uniquement à l'usage réel)."""
    try:
        import pyaudiowpatch as pyaudio  # type: ignore
        return pyaudio
    except ImportError as e:
        raise AudioStreamError(
            "PyAudioWPatch n'est pas installé. "
            "Installez-le avec: pip install pyaudiowpatch"
        ) from e


@dataclass
class DeviceInfo:
    """Information sur un périphérique audio."""
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    is_input: bool
    is_output: bool
    is_loopback: bool = False
    host_api: int = 0


class AudioManager:
    """
    Gestionnaire centralisé des périphériques et streams audio.

    Utilise PyAudioWPatch pour le support WASAPI loopback (Windows).

    Usage:
        manager = AudioManager()
        devices = manager.list_devices()

        input_stream = manager.open_input_stream(
            device_pattern="Microphone",
            config=audio_config,
        )

        loopback_stream = manager.open_loopback_stream(
            device_pattern="CABLE-B",
            config=audio_config,
        )
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._pyaudio: Optional[Any] = None
        self._pa_module: Optional[Any] = None
        self._streams: Dict[str, Any] = {}
        self._devices: List[DeviceInfo] = []

    @property
    def pyaudio(self):
        """Accès lazy à l'instance PyAudio."""
        if self._pyaudio is None:
            self._pa_module = _import_pyaudio()
            self._pyaudio = self._pa_module.PyAudio()
            self._scan_devices()
        return self._pyaudio

    def _scan_devices(self) -> None:
        self._devices = []
        for i in range(self._pyaudio.get_device_count()):
            try:
                info = self._pyaudio.get_device_info_by_index(i)
                device = DeviceInfo(
                    index=i,
                    name=info["name"],
                    max_input_channels=info["maxInputChannels"],
                    max_output_channels=info["maxOutputChannels"],
                    default_sample_rate=info["defaultSampleRate"],
                    is_input=info["maxInputChannels"] > 0,
                    is_output=info["maxOutputChannels"] > 0,
                    is_loopback="loopback" in info["name"].lower(),
                    host_api=info["hostApi"],
                )
                self._devices.append(device)
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"Erreur lecture device {i}: {e}")

    def list_devices(self, input_only: bool = False,
                     output_only: bool = False) -> List[DeviceInfo]:
        """Liste les périphériques audio disponibles."""
        _ = self.pyaudio
        devices = self._devices
        if input_only:
            devices = [d for d in devices if d.is_input]
        elif output_only:
            devices = [d for d in devices if d.is_output]
        return devices

    def find_device(self, pattern: str, input_only: bool = False,
                    output_only: bool = False) -> DeviceInfo:
        """Trouve un périphérique par motif de nom (insensible à la casse)."""
        devices = self.list_devices(input_only=input_only, output_only=output_only)
        pattern_lower = pattern.lower()
        for device in devices:
            if pattern_lower in device.name.lower():
                return device
        raise AudioDeviceNotFoundError(
            f"Périphérique '{pattern}' non trouvé. "
            f"Disponibles: {[d.name for d in devices]}"
        )

    def find_loopback_device(self, pattern: str) -> DeviceInfo:
        """Trouve un périphérique loopback WASAPI."""
        _ = self.pyaudio
        try:
            wasapi_info = self._pyaudio.get_host_api_info_by_type(
                self._pa_module.paWASAPI
            )
            for i in range(wasapi_info["deviceCount"]):
                device_info = self._pyaudio.get_device_info_by_host_api_device_index(
                    wasapi_info["index"], i
                )
                if (
                    pattern.lower() in device_info["name"].lower()
                    and device_info["maxInputChannels"] > 0
                ):
                    return DeviceInfo(
                        index=device_info["index"],
                        name=device_info["name"],
                        max_input_channels=device_info["maxInputChannels"],
                        max_output_channels=device_info["maxOutputChannels"],
                        default_sample_rate=device_info["defaultSampleRate"],
                        is_input=True,
                        is_output=False,
                        is_loopback=True,
                        host_api=wasapi_info["index"],
                    )

            # Fallback: certains pilotes exposent le loopback comme device "[Loopback]"
            for d in self._devices:
                if pattern.lower() in d.name.lower() and "loopback" in d.name.lower():
                    return d

            raise AudioDeviceNotFoundError(f"Loopback '{pattern}' non trouvé")
        except AudioDeviceNotFoundError:
            raise
        except Exception as e:  # noqa: BLE001
            raise AudioDeviceNotFoundError(
                f"Erreur recherche loopback '{pattern}': {e}"
            ) from e

    def get_default_input_device(self) -> DeviceInfo:
        try:
            info = self.pyaudio.get_default_input_device_info()
            return self._info_to_device(info)
        except Exception as e:  # noqa: BLE001
            raise AudioDeviceNotFoundError(
                f"Pas de périphérique d'entrée par défaut: {e}"
            ) from e

    def get_default_output_device(self) -> DeviceInfo:
        try:
            info = self.pyaudio.get_default_output_device_info()
            return self._info_to_device(info)
        except Exception as e:  # noqa: BLE001
            raise AudioDeviceNotFoundError(
                f"Pas de périphérique de sortie par défaut: {e}"
            ) from e

    def _info_to_device(self, info: Dict) -> DeviceInfo:
        return DeviceInfo(
            index=info["index"],
            name=info["name"],
            max_input_channels=info["maxInputChannels"],
            max_output_channels=info["maxOutputChannels"],
            default_sample_rate=info["defaultSampleRate"],
            is_input=info["maxInputChannels"] > 0,
            is_output=info["maxOutputChannels"] > 0,
            host_api=info["hostApi"],
        )

    def open_input_stream(self, config: AudioConfig,
                          device: Optional[DeviceInfo] = None,
                          device_pattern: Optional[str] = None,
                          stream_id: str = "input"):
        """Ouvre un stream d'entrée audio."""
        if device is None:
            if device_pattern:
                device = self.find_device(device_pattern, input_only=True)
            else:
                device = self.get_default_input_device()

        try:
            stream = self.pyaudio.open(
                format=self._pa_module.paInt16,
                channels=config.channels,
                rate=config.sample_rate,
                input=True,
                input_device_index=device.index,
                frames_per_buffer=config.chunk_size,
            )
            self._streams[stream_id] = stream
            self.logger.info(f"Stream input ouvert: {device.name}")
            return stream
        except Exception as e:  # noqa: BLE001
            raise AudioStreamError(f"Erreur ouverture stream input: {e}") from e

    def open_output_stream(self, config: AudioConfig,
                           device: Optional[DeviceInfo] = None,
                           device_pattern: Optional[str] = None,
                           stream_id: str = "output"):
        """Ouvre un stream de sortie audio."""
        if device is None:
            if device_pattern:
                device = self.find_device(device_pattern, output_only=True)
            else:
                device = self.get_default_output_device()

        try:
            stream = self.pyaudio.open(
                format=self._pa_module.paInt16,
                channels=config.channels,
                rate=config.sample_rate,
                output=True,
                output_device_index=device.index,
                frames_per_buffer=config.chunk_size,
            )
            self._streams[stream_id] = stream
            self.logger.info(f"Stream output ouvert: {device.name}")
            return stream
        except Exception as e:  # noqa: BLE001
            raise AudioStreamError(f"Erreur ouverture stream output: {e}") from e

    def open_loopback_stream(self, config: AudioConfig,
                             device_pattern: str,
                             stream_id: str = "loopback",
                             exclusive: bool = False):
        """Ouvre un stream loopback WASAPI.

        Args:
            config: configuration audio
            device_pattern: motif de nom du device loopback
            stream_id: id interne du stream
            exclusive: si True, ouvre le device en mode WASAPI exclusif.
                Avantage zero-trust : empêche d'autres applications de
                capturer simultanément le même périphérique (anti
                multi-tenant). Inconvénient : si une autre app utilise
                déjà le device, l'ouverture échoue.

                Note : tous les drivers ne supportent pas le mode exclusif
                sur leur sortie loopback. Si l'init échoue, on fallback
                automatiquement en mode partagé avec un warning.
        """
        device = self.find_loopback_device(device_pattern)

        host_api_specific_stream_info = None
        if exclusive:
            try:
                host_api_specific_stream_info = self._pa_module.PaWasapiStreamInfo(
                    flags=self._pa_module.paWinWasapiExclusive,
                )
            except Exception as e:  # noqa: BLE001
                self.logger.warning(
                    f"Impossible de configurer WASAPI exclusive ({e}), "
                    f"fallback partagé."
                )
                host_api_specific_stream_info = None

        try:
            open_kwargs = dict(
                format=self._pa_module.paInt16,
                channels=config.channels,
                rate=config.sample_rate,
                input=True,
                input_device_index=device.index,
                frames_per_buffer=config.chunk_size,
            )
            if host_api_specific_stream_info is not None:
                open_kwargs["input_host_api_specific_stream_info"] = (
                    host_api_specific_stream_info
                )

            stream = self.pyaudio.open(**open_kwargs)
            self._streams[stream_id] = stream
            mode = "exclusif" if host_api_specific_stream_info else "partagé"
            self.logger.info(f"Stream loopback ouvert ({mode}): {device.name}")
            return stream
        except Exception as e:  # noqa: BLE001
            # Fallback : si exclusif échoue (autre app déjà accrochée), on
            # retente en partagé pour ne pas planter l'app.
            if exclusive:
                self.logger.warning(
                    f"WASAPI exclusif refusé ({e}), retry en mode partagé. "
                    f"⚠ Le multi-tenant n'est PAS protégé sur ce stream."
                )
                try:
                    stream = self.pyaudio.open(
                        format=self._pa_module.paInt16,
                        channels=config.channels,
                        rate=config.sample_rate,
                        input=True,
                        input_device_index=device.index,
                        frames_per_buffer=config.chunk_size,
                    )
                    self._streams[stream_id] = stream
                    return stream
                except Exception as e2:  # noqa: BLE001
                    raise AudioStreamError(
                        f"Erreur ouverture stream loopback (les deux modes "
                        f"ont échoué): exclusif={e}, partagé={e2}"
                    ) from e2
            raise AudioStreamError(
                f"Erreur ouverture stream loopback: {e}"
            ) from e

    def close_stream(self, stream_id: str) -> None:
        if stream_id in self._streams:
            try:
                self._streams[stream_id].stop_stream()
                self._streams[stream_id].close()
                del self._streams[stream_id]
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"Erreur fermeture stream {stream_id}: {e}")

    def close_all(self) -> None:
        for stream_id in list(self._streams.keys()):
            self.close_stream(stream_id)
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"Erreur terminate PyAudio: {e}")
            self._pyaudio = None

    def print_devices(self) -> None:
        """Affiche tous les périphériques disponibles."""
        print("\n" + "=" * 70)
        print("🎚️  PÉRIPHÉRIQUES AUDIO")
        print("=" * 70)
        for device in self.list_devices():
            device_type = []
            if device.is_input:
                device_type.append("IN")
            if device.is_output:
                device_type.append("OUT")
            if device.is_loopback:
                device_type.append("LOOP")
            type_str = "/".join(device_type) or "?"
            print(f"[{device.index:2d}] {device.name}")
            print(
                f"      Type: {type_str}, Rate: {int(device.default_sample_rate)}Hz"
            )
        print("=" * 70)
