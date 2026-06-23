"""
Exceptions personnalisées pour le traducteur izvox.
"""


class TranslatorError(Exception):
    """Exception de base pour le traducteur."""
    pass


class HardwareError(TranslatorError):
    """Erreur liée au matériel (GPU, audio, etc.)."""
    pass


class ModelError(TranslatorError):
    """Erreur liée aux modèles AI."""
    pass


class ModelNotFoundError(ModelError):
    """Modèle non trouvé ou non téléchargé."""
    pass


class ModelLoadError(ModelError):
    """Erreur lors du chargement d'un modèle."""
    pass


class ModelDownloadError(ModelError):
    """Erreur lors du téléchargement d'un modèle."""
    pass


class AudioError(TranslatorError):
    """Erreur liée à l'audio."""
    pass


class AudioDeviceNotFoundError(AudioError):
    """Périphérique audio non trouvé."""
    pass


class AudioStreamError(AudioError):
    """Erreur de stream audio."""
    pass


class PipelineError(TranslatorError):
    """Erreur dans le pipeline de traduction."""
    pass


class ConfigurationError(TranslatorError):
    """Erreur de configuration."""
    pass
