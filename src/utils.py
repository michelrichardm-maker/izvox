"""
Utilitaires divers pour le traducteur izvox.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


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
