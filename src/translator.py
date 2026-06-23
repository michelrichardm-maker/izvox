"""
Traduction avec NLLB-200 (Meta) ou Opus-MT.

Traduit le texte entre langues avec haute qualité.
Le modèle est sélectionné automatiquement par ModelManager selon le matériel:
  - NLLB-200 (3.3B / 1.3B / 600M) pour GPU
  - Opus-MT (Helsinki-NLP) pour CPU
"""

import logging
from typing import Dict

from .config import TranslationConfig
from .exceptions import ModelLoadError


class TranslatorProcessor:
    """
    Processeur de traduction basé sur NLLB-200 ou Opus-MT.

    Usage:
        translator = TranslatorProcessor(config)
        text_en = translator.translate("Bonjour", "fr", "en")
    """

    NLLB_LANG_CODES: Dict[str, str] = {
        "fr": "fra_Latn",
        "en": "eng_Latn",
        "es": "spa_Latn",
        "de": "deu_Latn",
        "it": "ita_Latn",
        "pt": "por_Latn",
        "nl": "nld_Latn",
        "pl": "pol_Latn",
        "ru": "rus_Cyrl",
        "zh": "zho_Hans",
        "ja": "jpn_Jpan",
        "ko": "kor_Hang",
        "ar": "arb_Arab",
    }

    def __init__(self, config: TranslationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        self.tokenizer = None
        self.model = None
        self.is_nllb = "nllb" in config.model_name.lower()

        self._load_model()

    def _load_model(self) -> None:
        self.logger.info(f"Chargement modèle: {self.config.model_name}...")
        try:
            import torch  # type: ignore
            from transformers import (  # type: ignore
                AutoTokenizer,
                AutoModelForSeq2SeqLM,
            )

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name, cache_dir=self.config.cache_dir
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.config.model_name, cache_dir=self.config.cache_dir
            )

            if self.config.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.to("cuda")

            self.model.eval()
            self.logger.info(
                f"✓ Modèle de traduction chargé sur {self.config.device}"
            )
        except ImportError as e:
            raise ModelLoadError(
                "transformers/torch non installé. "
                "Installez avec: pip install transformers torch"
            ) from e
        except Exception as e:
            self.logger.error(f"Erreur chargement traduction: {e}")
            raise ModelLoadError(f"Erreur chargement traduction: {e}") from e

    def translate(self, text: str, source_lang: str = "fr",
                  target_lang: str = "en") -> str:
        """Traduit un texte d'une langue à une autre."""
        if not text or not text.strip():
            return ""
        try:
            if self.is_nllb:
                return self._translate_nllb(text, source_lang, target_lang)
            return self._translate_opus(text)
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Erreur traduction: {e}")
            return text

    def _translate_nllb(self, text: str, source_lang: str,
                        target_lang: str) -> str:
        import torch  # type: ignore

        src_code = self.NLLB_LANG_CODES.get(source_lang, "fra_Latn")
        tgt_code = self.NLLB_LANG_CODES.get(target_lang, "eng_Latn")

        self.tokenizer.src_lang = src_code

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
        )

        if self.config.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        # Compat: certains tokenizers exposent convert_tokens_to_ids au lieu
        # de lang_code_to_id
        if hasattr(self.tokenizer, "lang_code_to_id"):
            forced_bos_token_id = self.tokenizer.lang_code_to_id[tgt_code]
        else:
            forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_code)

        with torch.no_grad():
            generated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=self.config.max_length,
                num_beams=self.config.num_beams,
                early_stopping=True,
            )

        translation = self.tokenizer.batch_decode(
            generated_tokens, skip_special_tokens=True
        )[0]
        return translation.strip()

    def _translate_opus(self, text: str) -> str:
        import torch  # type: ignore

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
        )

        if self.config.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            generated_tokens = self.model.generate(
                **inputs,
                max_length=self.config.max_length,
                num_beams=self.config.num_beams,
                early_stopping=True,
            )

        translation = self.tokenizer.batch_decode(
            generated_tokens, skip_special_tokens=True
        )[0]
        return translation.strip()

    def set_languages(self, source_lang: str, target_lang: str) -> None:
        """Configure les langues source et cible."""
        self.config.source_lang = self.NLLB_LANG_CODES.get(source_lang, source_lang)
        self.config.target_lang = self.NLLB_LANG_CODES.get(target_lang, target_lang)
