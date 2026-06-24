"""
Redaction des transcripts dans les logs.

Par défaut, izvox masque le contenu textuel des transcriptions/traductions
quand il les écrit dans les logs. Le contrôle se fait via la config
(`AppConfig.redact_logs`), pas directement dans ce module — celui-ci
n'expose qu'un helper pur.
"""

from __future__ import annotations


def redact(text: str | None, lang: str = "??") -> str:
    """
    Retourne une représentation non-révélatrice d'un texte.

    Exemple :
        redact("Bonjour le monde", "fr")
        # -> "[FR 16 chars / 3 words]"

    Args:
        text: Texte original à masquer (peut être None ou vide).
        lang: Code de langue (2 lettres en général) à inclure dans le tag.
    """
    if text is None:
        return f"[{lang.upper()} <none>]"
    text = text.strip()
    if not text:
        return f"[{lang.upper()} <empty>]"
    n_chars = len(text)
    n_words = len(text.split())
    return f"[{lang.upper()} {n_chars} chars / {n_words} words]"


def maybe_redact(text: str | None, lang: str, redact_enabled: bool) -> str:
    """Helper qui applique `redact` selon le drapeau de config."""
    if redact_enabled:
        return redact(text, lang)
    return text if text is not None else ""
