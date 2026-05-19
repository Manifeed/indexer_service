from __future__ import annotations

import os
from functools import lru_cache
from typing import Protocol


MONOLINGUAL_COUNTRY_LANGUAGES: dict[str, str] = {
    "fr": "fr",
    "it": "it",
    "de": "de",
    "es": "es",
    "pt": "pt",
    "nl": "nl",
    "pl": "pl",
    "se": "sv",
    "dk": "da",
    "no": "no",
    "fi": "fi",
    "gr": "el",
    "cz": "cs",
    "sk": "sk",
    "hu": "hu",
    "ro": "ro",
    "bg": "bg",
    "tr": "tr",
    "jp": "ja",
    "kr": "ko",
    "cn": "zh",
    "ru": "ru",
    "us": "en",
    "uk": "en",
    "gb": "en",
}


class FastTextLikeDetector(Protocol):
    def predict(self, text: str, k: int = 1): ...


def detect_article_language(
    *,
    country: str | None,
    title: str,
    summary: str | None,
    detector: FastTextLikeDetector | None = None,
) -> str:
    normalized_country = (country or "").strip().casefold()[:2]
    country_language = MONOLINGUAL_COUNTRY_LANGUAGES.get(normalized_country)
    if country_language is not None:
        return country_language
    return detect_text_language(text=_build_language_detection_text(title, summary), detector=detector)


def detect_text_language(
    *,
    text: str,
    detector: FastTextLikeDetector | None = None,
) -> str:
    normalized_text = text.strip()
    if not normalized_text:
        return "xx"
    active_detector = detector or get_fasttext_language_detector()
    if active_detector is None:
        return "xx"
    try:
        labels, _scores = active_detector.predict(normalized_text.replace("\n", " "), k=1)
    except Exception:
        return "xx"
    if not labels:
        return "xx"
    label = str(labels[0]).replace("__label__", "").strip().casefold()
    return label[:2] if len(label) >= 2 else "xx"


@lru_cache(maxsize=1)
def get_fasttext_language_detector() -> FastTextLikeDetector | None:
    model_path = os.getenv("LANGUAGE_FASTTEXT_MODEL_PATH", "").strip()
    if not model_path:
        return None
    try:
        import fasttext  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        return fasttext.load_model(model_path)
    except Exception:
        return None


def _build_language_detection_text(title: str, summary: str | None) -> str:
    return "\n\n".join(part.strip() for part in (title, summary or "") if part and part.strip())
