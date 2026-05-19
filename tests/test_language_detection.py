from __future__ import annotations

from app.domain.language_detection import detect_article_language


class FakeFastTextDetector:
    def predict(self, text: str, k: int = 1):
        assert "Bundestag" in text
        assert k == 1
        return ["__label__de"], [0.98]


def test_detect_article_language_uses_monolingual_country_before_fasttext() -> None:
    assert (
        detect_article_language(
            country="fr",
            title="English title should not matter",
            summary=None,
            detector=FakeFastTextDetector(),
        )
        == "fr"
    )


def test_detect_article_language_uses_fasttext_for_ambiguous_country() -> None:
    assert (
        detect_article_language(
            country="eu",
            title="Bundestag stimmt ab",
            summary=None,
            detector=FakeFastTextDetector(),
        )
        == "de"
    )


def test_detect_article_language_falls_back_to_unknown_without_detector() -> None:
    assert detect_article_language(country="eu", title="Text", summary=None, detector=None) == "xx"
