"""
Utilitaires divers pour le traducteur izvox.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np


def setup_logging(level: str = "INFO", log_file: Optional[str] = None,
                  use_color: bool = True) -> None:
    """
    Configure le système de logging.

    Args:
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        log_file: Chemin optionnel vers un fichier de log
        use_color: Active la coloration des logs si colorlog est disponible
    """
    handlers: list[logging.Handler] = []

    stream_handler: logging.Handler
    if use_color:
        try:
            import colorlog  # type: ignore

            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(
                colorlog.ColoredFormatter(
                    "%(log_color)s%(asctime)s [%(levelname)s]%(reset)s "
                    "%(name)s: %(message)s",
                    datefmt="%H:%M:%S",
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red,bg_white",
                    },
                )
            )
        except ImportError:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
    else:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    handlers.append(stream_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in handlers:
        root_logger.addHandler(handler)


def format_duration(seconds: float) -> str:
    """Formate une durée en chaîne lisible."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(seconds, 60)
    return f"{int(minutes)}m {sec:.0f}s"


def format_size(num_bytes: int) -> str:
    """Formate une taille en bytes en chaîne lisible."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def ensure_directory(path: Path) -> Path:
    """Crée un répertoire s'il n'existe pas et le retourne."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resample_pcm(audio_bytes: bytes, src_rate: int, dst_rate: int) -> bytes:
    """
    Rééchantillonne du PCM int16 d'un sample-rate vers un autre.

    Préfère scipy.signal.resample_poly (haute qualité) si scipy est
    installé. Sinon fallback sur np.interp (suffisant pour des
    différences modérées comme 22050↔16000).

    Args:
        audio_bytes: PCM mono, dtype int16
        src_rate: sample-rate d'origine
        dst_rate: sample-rate cible

    Returns:
        PCM int16 rééchantillonné (bytes)
    """
    if src_rate == dst_rate or not audio_bytes:
        return audio_bytes

    audio = np.frombuffer(audio_bytes, dtype=np.int16)
    if audio.size == 0:
        return audio_bytes

    try:
        from scipy.signal import resample_poly  # type: ignore

        from math import gcd
        g = gcd(src_rate, dst_rate)
        up = dst_rate // g
        down = src_rate // g
        resampled = resample_poly(audio.astype(np.float32), up, down)
    except ImportError:
        # Fallback: interpolation linéaire
        duration = audio.size / src_rate
        new_size = int(round(duration * dst_rate))
        if new_size <= 0:
            return b""
        old_idx = np.arange(audio.size, dtype=np.float64)
        new_idx = np.linspace(0, audio.size - 1, new_size, dtype=np.float64)
        resampled = np.interp(new_idx, old_idx, audio.astype(np.float32))

    # Clipping + retour en int16
    resampled = np.clip(resampled, -32768, 32767).astype(np.int16)
    return resampled.tobytes()


def print_banner() -> None:
    """Affiche la bannière de l'application."""
    banner = r"""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║          🌍  IZVOX - Traducteur Bidirectionnel  🌍               ║
    ║                                                                  ║
    ║              FR ⇄ EN  |  100% local  |  <600ms                   ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)
