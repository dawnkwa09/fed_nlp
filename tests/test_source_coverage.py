from __future__ import annotations

import pandas as pd
import pytest

from fed_nlp.source_coverage import audit_source_coverage, validate_source_coverage, yearly_source_counts


@pytest.fixture
def healthy_documents() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [
                "2020-01-15",
                "2020-01-20",
                "2021-02-01",
                "2021-02-11",
                "2022-05-10",
                "2022-05-15",
            ],
            "source_type": [
                "beigebook",
                "statement",
                "beigebook",
                "statement",
                "beigebook",
                "statement",
            ],
        }
    )


def test_yearly_source_counts_aggregate_by_year_and_source(healthy_documents: pd.DataFrame) -> None:
    counts = yearly_source_counts(healthy_documents)

    assert list(counts.columns) == ["year", "source_type", "document_count"]
    assert counts["document_count"].sum() == 6
    assert counts[(counts["year"] == 2020) & (counts["source_type"] == "beigebook")]["document_count"].item() == 1
    assert counts[(counts["year"] == 2021) & (counts["source_type"] == "statement")]["document_count"].item() == 1


def test_audit_marks_observed_gaps_as_flagged() -> None:
    dates = [
        *[f"2020-01-{day:02d}" for day in range(1, 11)],
        *[f"2021-01-{day:02d}" for day in range(1, 9)],
        *[f"2022-01-{day:02d}" for day in range(1, 3)],
        *["2023-01-10"],
    ]
    sources = ["beigebook"] * 10 + ["beigebook"] * 8 + ["beigebook"] * 2 + ["statement"]

    documents = pd.DataFrame({"date": dates, "source_type": sources})

    audit = audit_source_coverage(documents, minimum_observed_docs=1)
    flagged = audit["flagged_rows"]

    assert audit["is_complete"] is False
    assert not flagged.empty
    assert "beigebook" in set(flagged["source_type"])


def test_validate_source_coverage_raises_on_coverage_problem() -> None:
    with pytest.raises(ValueError):
        validate_source_coverage(
            pd.DataFrame(
                {
                    "date": [
                        "2020-01-01",
                        "2020-01-02",
                        "2020-01-03",
                        "2020-01-04",
                        "2021-01-01",
                        "2021-01-02",
                        "2021-01-03",
                        "2021-01-04",
                        "2022-01-01",
                    ],
                    "source_type": [
                        "beigebook",
                        "beigebook",
                        "beigebook",
                        "beigebook",
                        "beigebook",
                        "beigebook",
                        "beigebook",
                        "beigebook",
                        "beigebook",
                    ],
                }
            ),
            minimum_observed_docs=2,
        )

    healthy_documents = pd.DataFrame(
        {
            "date": [
                "2020-01-15",
                "2020-01-20",
                "2021-02-01",
                "2021-02-11",
                "2022-05-10",
                "2022-05-15",
            ],
            "source_type": [
                "beigebook",
                "statement",
                "beigebook",
                "statement",
                "beigebook",
                "statement",
            ],
        }
    )
    result = validate_source_coverage(healthy_documents, minimum_observed_docs=1)
    assert result["is_complete"]
