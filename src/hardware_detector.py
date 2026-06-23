"""
Détection automatique des capacités matérielles.

Détermine le meilleur profil de configuration selon le GPU/CPU disponible.
Supporte NVIDIA (CUDA), AMD/Intel (DirectML) et fallback CPU.
"""

import logging
import os
import platform
from dataclasses import dataclass
from typing import Optional

from .config import HardwareLevel


@dataclass
class HardwareInfo:
    """Informations détaillées sur le matériel."""
    has_cuda: bool = False
    has_directml: bool = False
    gpu_name: str = "None"
    vram_mb: int = 0
    cuda_version: Optional[str] = None

    cpu_name: str = ""
    cpu_cores: int = 1
    cpu_threads: int = 1

    ram_gb: float = 0.0

    level: HardwareLevel = HardwareLevel.CPU_ONLY
    recommended_device: str = "cpu"


class HardwareDetector:
    """
    Détecte les capacités matérielles du système.

    Usage:
        detector = HardwareDetector()
        hw_info = detector.detect()
        print(f"GPU: {hw_info.gpu_name}")
        print(f"Niveau recommandé: {hw_info.level}")
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def detect(self) -> HardwareInfo:
        """Effectue la détection complète du matériel."""
        info = HardwareInfo()

        self._detect_cpu(info)
        self._detect_ram(info)
        self._detect_cuda(info)

        if not info.has_cuda and platform.system() == "Windows":
            self._detect_directml(info)

        self._determine_level(info)
        return info

    def _detect_cpu(self, info: HardwareInfo) -> None:
        info.cpu_cores = os.cpu_count() or 1
        info.cpu_threads = info.cpu_cores

        try:
            import cpuinfo  # type: ignore
            cpu_info = cpuinfo.get_cpu_info()
            info.cpu_name = cpu_info.get("brand_raw", "Unknown CPU")
        except ImportError:
            info.cpu_name = platform.processor() or "Unknown CPU"
        except Exception as e:  # noqa: BLE001
            self.logger.debug(f"cpuinfo échec: {e}")
            info.cpu_name = platform.processor() or "Unknown CPU"

    def _detect_ram(self, info: HardwareInfo) -> None:
        try:
            import psutil  # type: ignore
            info.ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            self.logger.debug("psutil indisponible, RAM estimée")
            info.ram_gb = 8.0

    def _detect_cuda(self, info: HardwareInfo) -> None:
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                info.has_cuda = True
                info.gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                info.vram_mb = props.total_memory // (1024 * 1024)
                info.cuda_version = torch.version.cuda
                info.recommended_device = "cuda"
                self.logger.info(
                    f"CUDA détecté: {info.gpu_name} ({info.vram_mb}MB)"
                )
        except ImportError:
            self.logger.debug("PyTorch non installé, détection CUDA ignorée")
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Erreur détection CUDA: {e}")

    def _detect_directml(self, info: HardwareInfo) -> None:
        try:
            import torch_directml  # type: ignore  # noqa: F401
            info.has_directml = True
            info.gpu_name = "DirectML Compatible GPU"
            info.vram_mb = 4096
            info.recommended_device = "privateuseone"
            self.logger.info("DirectML détecté")
        except ImportError:
            self.logger.debug("torch-directml non installé")

    def _determine_level(self, info: HardwareInfo) -> None:
        if info.has_cuda:
            if info.vram_mb >= 12000:
                info.level = HardwareLevel.HIGH
            elif info.vram_mb >= 6000:
                info.level = HardwareLevel.MEDIUM
            else:
                info.level = HardwareLevel.LOW
        elif info.has_directml:
            info.level = HardwareLevel.MEDIUM
        else:
            info.level = HardwareLevel.CPU_ONLY
            info.recommended_device = "cpu"

    def print_info(self, info: HardwareInfo) -> None:
        """Affiche les informations matérielles de manière formatée."""
        print("\n" + "=" * 70)
        print("🖥️  DÉTECTION MATÉRIELLE")
        print("=" * 70)
        print(f"CPU: {info.cpu_name}")
        print(f"Cores/Threads: {info.cpu_cores}/{info.cpu_threads}")
        print(f"RAM: {info.ram_gb:.1f} GB")
        print()
        print(f"GPU: {info.gpu_name}")
        print(f"VRAM: {info.vram_mb} MB")
        cuda_status = "✓ " + (info.cuda_version or "") if info.has_cuda else "✗"
        print(f"CUDA: {cuda_status}")
        print(f"DirectML: {'✓' if info.has_directml else '✗'}")
        print()
        print(f"🎯 Niveau recommandé: {info.level.value.upper()}")
        print(f"📍 Device: {info.recommended_device}")
        print("=" * 70)
