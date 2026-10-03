from __future__ import annotations

import pandas as pd
import pytest

from fed_nlp.canonical_corpus import build_canonical_corpus, validate_canonical_corpus


def test_build_canonical_corpus_standardizes_metadata_and_dates() -> None:
    documents = [
        {
            "date": "2020-01-15",
            "source": "Beige Book",
            "title": "January Beige Book",
            "author": "Lael Brainard",
            "text": "Inflation remains elevated.",
            "url": "https://example.com/beige",
        },
        {
            "date": "2021-05-01",
            "source_type": "speech",
            "title": "Talk on inflation",
            "speaker": "",
            "body": "Growth is slowing and unemployment is stable.",
            "link": "https://example.com/speech",
        },
    ]

    corpus = build_canonical_corpus(documents, start_year=2000)

    assert set(corpus.columns) >= {
        "document_id",
        "source_type",
        "date",
        "title",
        "speaker",
        "chair",
        "raw_text",
        "cleaned_text",
        "url",
        "document_weight",
        "review_required",
        "missing_author",
    }
    assert corpus["source_type"].tolist() == ["beigebook", "speech"]
    assert corpus["document_weight"].tolist() == [1.0, 1.0]
    assert corpus["review_required"].tolist() == [False, True]
    assert corpus["missing_author"].tolist() == [False, True]
    assert pd.Timestamp("2020-01-15") == corpus.loc[0, "date"]
    assert corpus.loc[1, "url"] == "https://example.com/speech"


def test_build_canonical_corpus_prints_manual_review_for_missing_speaker(capsys: pytest.CaptureFixture[str]) -> None:
    documents = [{
        "date": "2022-02-10",
        "source_type": "statement",
        "title": "Statement",
        "speaker": "",
        "url": "https://example.com/review-me",
        "text": "Inflation concerns remain elevated.",
    }]

    build_canonical_corpus(documents)
    stdout = capsys.readouterr().out
    assert "Manual review required" in stdout
    assert "https://example.com/review-me" in stdout


def test_validate_canonical_corpus_accepts_standardized_document_table() -> None:
    corpus = pd.DataFrame(
        {
            "document_id": ["doc-1", "doc-2"],
            "source_type": ["statement", "beigebook"],
            "date": pd.to_datetime(["2020-02-01", "2021-03-01"]),
            "title": ["Statement", "Beige Book"],
            "speaker": ["Jerome Powell", ""],
            "chair": ["Jerome Powell", ""],
            "raw_text": ["Inflation", "Growth"],
            "cleaned_text": ["inflation", "growth"],
            "url": ["https://example.com/one", "https://example.com/two"],
            "document_weight": [1.0, 1.0],
            "review_required": [False, True],
            "missing_author": [False, True],
        }
    )

    result = validate_canonical_corpus(corpus)
    assert result["is_valid"] is True
    assert result["document_count"] == 2
    assert result["review_required_count"] == 1
