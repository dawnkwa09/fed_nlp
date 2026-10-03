"""Source coverage and publication checks for Phase 1 of the project."""

from __future__ import annotations

import argparse
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
