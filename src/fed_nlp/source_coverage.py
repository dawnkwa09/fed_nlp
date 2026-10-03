"""Source coverage and publication checks for Phase 1 of the project."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_DATE_COLUMN = "date"
DEFAULT_SOURCE_COLUMN = "source_type"


def yearly_source_counts(
    df: pd.DataFrame,
    date_col: str = DEFAULT_DATE_COLUMN,
    source_col: str = DEFAULT_SOURCE_COLUMN,
) -> pd.DataFrame:
    """Return a yearly document count for each source type."""
    frame = df.copy()
    if frame.empty:
        return pd.DataFrame(columns=["year", "source_type", "document_count"])

    if date_col not in frame.columns:
        raise KeyError(f"Date column '{date_col}' not found in the input data.")
    if source_col not in frame.columns:
        raise KeyError(f"Source column '{source_col}' not found in the input data.")

    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    frame = frame.dropna(subset=[date_col]).copy()
    frame["year"] = frame[date_col].dt.year
    frame[source_col] = frame[source_col].fillna("unknown").astype(str).str.strip()
    frame[source_col] = frame[source_col].replace({"": "unknown"})

    counts = (
        frame.groupby(["year", source_col], dropna=False)
        .size()
        .rename("document_count")
        .reset_index()
        .rename(columns={source_col: "source_type"})
    )
    return counts.sort_values(["year", "source_type"]).reset_index(drop=True)


def detect_coverage_gaps(
    counts: pd.DataFrame,
    year_col: str = "year",
    source_col: str = "source_type",
    count_col: str = "document_count",
    decline_threshold: float = 0.5,
    minimum_observed_docs: int = 10,
) -> pd.DataFrame:
    """Flag large coverage gaps or abrupt drops in a yearly source count table."""
    if counts.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "source_type",
                "document_count",
                "median_count",
                "year_over_year_change",
                "status",
                "reason",
            ]
        )

    required_columns = {year_col, source_col, count_col}
    missing = required_columns - set(counts.columns)
    if missing:
        raise KeyError(f"Counts input is missing required columns: {sorted(missing)}")

    results = []
    for source, group in counts.groupby(source_col, sort=True):
        group = group.sort_values(year_col).copy()
        median_count = float(group[count_col].median())
        previous_year_count: int | None = None

        for _, row in group.iterrows():
            current_year = int(row[year_col])
            count = int(row[count_col])
            year_over_year_change = None
            status = "ok"
            reason = "ok"

            if previous_year_count is not None:
                denominator = previous_year_count if previous_year_count != 0 else 1.0
                year_over_year_change = (count - previous_year_count) / denominator
                if (
                    previous_year_count >= minimum_observed_docs
                    and year_over_year_change <= -decline_threshold
                ):
                    status = "flagged"
                    reason = "abrupt_drop"

            if count == 0:
                status = "flagged"
                reason = "missing_data"
            elif (
                median_count > minimum_observed_docs
                and count < max(minimum_observed_docs, median_count * decline_threshold)
            ):
                status = "flagged"
                reason = "coverage_gap"

            results.append(
                {
                    year_col: current_year,
                    source_col: source,
                    count_col: count,
                    "median_count": median_count,
                    "year_over_year_change": year_over_year_change,
                    "status": status,
                    "reason": reason,
                }
            )

            previous_year_count = count

    return pd.DataFrame(results).sort_values([source_col, year_col]).reset_index(drop=True)


def audit_source_coverage(
    df: pd.DataFrame,
    date_col: str = DEFAULT_DATE_COLUMN,
    source_col: str = DEFAULT_SOURCE_COLUMN,
    decline_threshold: float = 0.5,
    minimum_observed_docs: int = 10,
) -> dict[str, Any]:
    """Assess whether the corpus has material source coverage problems."""
    counts = yearly_source_counts(df, date_col=date_col, source_col=source_col)
    flags = detect_coverage_gaps(
        counts,
        decline_threshold=decline_threshold,
        minimum_observed_docs=minimum_observed_docs,
    )
    flagged = flags[flags["status"] == "flagged"].copy()

    return {
        "yearly_counts": counts,
        "coverage_flags": flags,
        "flagged_rows": flagged,
        "is_complete": flagged.empty,
    }


def validate_source_coverage(
    df: pd.DataFrame,
    date_col: str = DEFAULT_DATE_COLUMN,
    source_col: str = DEFAULT_SOURCE_COLUMN,
    decline_threshold: float = 0.5,
    minimum_observed_docs: int = 10,
) -> dict[str, Any]:
    """Return the audit and raise a ValueError for material coverage problems."""
    audit = audit_source_coverage(
        df,
        date_col=date_col,
        source_col=source_col,
        decline_threshold=decline_threshold,
        minimum_observed_docs=minimum_observed_docs,
    )
    if not audit["is_complete"]:
        raise ValueError(
            "Source coverage is incomplete. Review flagged rows before using the corpus: "
            + str(audit["flagged_rows"].to_dict(orient="records"))
        )
    return audit


def _read_input(input_path: str | Path) -> pd.DataFrame:
    path = Path(input_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported input format: {suffix}. Use .csv or .parquet.")


def _normalize_source_type(value: Any) -> str:
    if pd.isna(value):
        return "unknown"

    normalized = str(value).strip().lower().replace("_", " ").replace("-", " ")
    aliases = {
        "beigebook": "beigebook",
        "beige book": "beigebook",
        "beige book report": "beigebook",
        "beige-book": "beigebook",
        "statement": "statement",
        "statements": "statement",
        "minutes": "minutes",
        "minute": "minutes",
        "fomc minutes": "minutes",
        "speech": "speech",
        "speeches": "speech",
        "testimony": "speech",
        "speech testimony": "speech",
        "speechs": "speech",
        "unknown": "unknown",
    }
    return aliases.get(normalized, normalized)


def _canonical_column_mapping() -> dict[str, str]:
    return {
        "document_id": "document_id",
        "id": "document_id",
        "doc_id": "document_id",
        "source_type": "source_type",
        "document_type": "source_type",
        "source": "source_type",
        "publication_type": "source_type",
        "date": "date",
        "publication_date": "date",
        "release_date": "date",
        "document_date": "date",
        "title": "title",
        "document_title": "title",
        "speaker": "speaker",
        "speaker_name": "speaker",
        "author": "speaker",
        "author_name": "speaker",
        "chair": "chair",
        "chair_name": "chair",
        "fed_chair": "chair",
        "text": "raw_text",
        "raw_text": "raw_text",
        "content": "raw_text",
        "body": "raw_text",
        "transcript": "raw_text",
        "cleaned_text": "cleaned_text",
        "processed_text": "cleaned_text",
        "url": "url",
        "source_url": "url",
        "link": "url",
    }


def canonicalize_document_schema(
    documents: pd.DataFrame | list[dict[str, Any]] | None,
    date_col: str = DEFAULT_DATE_COLUMN,
    source_col: str = DEFAULT_SOURCE_COLUMN,
) -> pd.DataFrame:
    """Standardize a raw collection of Fed documents into a canonical document schema."""
    if documents is None:
        documents = []
    if isinstance(documents, list):
        frame = pd.DataFrame(documents)
    elif isinstance(documents, pd.DataFrame):
        frame = documents.copy()
    else:
        raise TypeError("documents must be a pandas DataFrame or a list of dictionaries.")

    if frame.empty:
        empty = pd.DataFrame(columns=[
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
        ])
        return empty

    canonical_columns = _canonical_column_mapping()
    rename_map = {}
    for current_name in list(frame.columns):
        candidate = canonical_columns.get(str(current_name), str(current_name))
        if current_name != candidate:
            rename_map[current_name] = candidate
    frame = frame.rename(columns=rename_map)

    if date_col != "date" and date_col in frame.columns:
        frame = frame.rename(columns={date_col: "date"})
    if source_col != "source_type" and source_col in frame.columns:
        frame = frame.rename(columns={source_col: "source_type"})

    for target in list(dict.fromkeys(frame.columns)):
        matching = [column for column in frame.columns if column == target]
        if len(matching) <= 1:
            continue
        combined = frame[matching].fillna("").astype(str)
        value = combined.iloc[:, 0].copy()
        for idx in range(1, len(matching)):
            value = value.mask(value.str.strip().eq(""), combined.iloc[:, idx])
        frame = frame.drop(columns=matching)
        frame[target] = value

    def _get_or_default(column_name: str, default_value: Any) -> pd.Series:
        if column_name in frame.columns:
            return frame[column_name]
        return pd.Series([default_value] * len(frame), index=frame.index)

    frame["source_type"] = _get_or_default("source_type", "unknown").map(_normalize_source_type)
    frame["date"] = pd.to_datetime(_get_or_default("date", pd.NaT), errors="coerce")
    frame["title"] = _get_or_default("title", "").fillna("").astype(str).str.strip()
    frame["speaker"] = _get_or_default("speaker", "").fillna("").astype(str).str.strip()
    frame["chair"] = _get_or_default("chair", "").fillna("").astype(str).str.strip()
    frame["raw_text"] = _get_or_default("raw_text", "").fillna("").astype(str)
    frame["cleaned_text"] = _get_or_default("cleaned_text", frame["raw_text"]).fillna("").astype(str)
    frame["url"] = _get_or_default("url", "").fillna("").astype(str).str.strip()

    if "document_id" not in frame.columns:
        frame["document_id"] = [
            hashlib.md5(
                (
                    f"{source}|{date}|{title}|{speaker}|{url}"
                ).encode("utf-8")
            ).hexdigest()
            for source, date, title, speaker, url in zip(
                frame["source_type"],
                frame["date"].dt.strftime("%Y-%m-%d").fillna("unknown"),
                frame["title"],
                frame["speaker"],
                frame["url"],
            )
        ]

    frame["document_weight"] = 1.0
    frame["review_required"] = False
    frame["missing_author"] = frame["speaker"].str.strip().eq("")
    frame.loc[frame["missing_author"], "review_required"] = True
    if "date" in frame.columns:
        frame.loc[frame["date"].isna(), "review_required"] = True

    return frame[
        [
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
        ]
    ].reset_index(drop=True)


def review_missing_authors(corpus: pd.DataFrame) -> pd.DataFrame:
    """Return the subset of a canonical corpus that requires manual review because it is unattributed."""
    required_columns = {"document_id", "source_type", "date", "title", "speaker", "url", "review_required"}
    missing = required_columns - set(corpus.columns)
    if missing:
        raise KeyError(f"Corpus is missing required review columns: {sorted(missing)}")

    return corpus[corpus["review_required"] == True].copy().sort_values(["source_type", "date", "document_id"]).reset_index(drop=True)


def build_canonical_corpus(
    documents: pd.DataFrame | list[dict[str, Any]] | None,
    start_year: int = 2000,
    date_col: str = DEFAULT_DATE_COLUMN,
    source_col: str = DEFAULT_SOURCE_COLUMN,
) -> pd.DataFrame:
    """Build a canonical corpus from raw Fed metadata, preserving missing metadata as review flags."""
    corpus = canonicalize_document_schema(documents, date_col=date_col, source_col=source_col)
    if corpus.empty:
        return corpus

    start_date = pd.Timestamp(f"{start_year}-01-01")
    corpus = corpus[(corpus["date"].isna()) | (corpus["date"] >= start_date)].copy()
    review_rows = review_missing_authors(corpus)

    if not review_rows.empty:
        print("Manual review required for documents without a clear author:")
        print(
            review_rows[["source_type", "date", "title", "speaker", "url"]]
            .fillna({"date": "missing", "url": "missing"})
            .to_string(index=False)
        )

    return corpus.reset_index(drop=True)


def validate_canonical_corpus(
    corpus: pd.DataFrame,
    start_year: int = 2000,
) -> dict[str, Any]:
    """Validate the canonical corpus for ingestion and document-level analysis readiness."""
    required_columns = {
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
    missing = required_columns - set(corpus.columns)
    if missing:
        raise KeyError(f"Corpus is missing required canonical columns: {sorted(missing)}")

    if corpus.empty:
        raise ValueError("The canonical corpus is empty; no documents were ingested.")

    valid_dates = corpus["date"].notna()
    if valid_dates.sum() == 0:
        raise ValueError("The canonical corpus contains no valid publication dates after standardization.")

    if corpus["source_type"].fillna("unknown").astype(str).str.strip().eq("").any():
        raise ValueError("At least one document has an empty source_type after normalization.")

    if ((corpus["date"].notna()) & (corpus["date"].dt.year < start_year)).any():
        raise ValueError("The canonical corpus contains documents that fall before the analysis window.")

    review = review_missing_authors(corpus)
    return {
        "is_valid": True,
        "document_count": int(len(corpus)),
        "review_required_count": int(len(review)),
        "review_required_rows": review,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the source coverage audit for the Fed corpus.")
    parser.add_argument("--input", required=True, type=str, help="Path to the corpus CSV or Parquet file.")
    args = parser.parse_args()

    df = _read_input(args.input)
    audit = audit_source_coverage(df)
    print(audit["yearly_counts"].to_string(index=False))

    if not audit["is_complete"]:
        print("\nCoverage issues detected:")
        print(audit["flagged_rows"].to_string(index=False))
        raise SystemExit(1)

    print("\nSource coverage passed all checks.")


if __name__ == "__main__":
    main()
