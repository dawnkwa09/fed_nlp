"""Canonical corpus construction for the Fed inflation-mindshare pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from fed_nlp.source_coverage import (
    _read_input,
    build_canonical_corpus,
    canonicalize_document_schema,
    review_missing_authors,
    validate_canonical_corpus,
)

__all__ = [
    "build_canonical_corpus",
    "canonicalize_document_schema",
    "review_missing_authors",
    "validate_canonical_corpus",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the raw Fed corpus and standardize it to the canonical schema.")
    parser.add_argument("--input", required=True, type=str, help="Path to the raw corpus CSV or Parquet file.")
    parser.add_argument("--output", type=str, default=None, help="Optional output path for the canonical corpus (*.csv or *.parquet).")
    parser.add_argument("--start-year", type=int, default=2000, help="Minimum publication year to include in the analysis window.")
    args = parser.parse_args()

    raw_documents = _read_input(Path(args.input))
    canonical = build_canonical_corpus(raw_documents, start_year=args.start_year)
    validate_canonical_corpus(canonical, start_year=args.start_year)

    if args.output:
        output_path = Path(args.output)
        if output_path.suffix.lower() == ".csv":
            canonical.to_csv(output_path, index=False)
        elif output_path.suffix.lower() == ".parquet":
            canonical.to_parquet(output_path, index=False)
        else:
            raise ValueError("Unsupported output format. Use .csv or .parquet.")

    print(f"Canonical corpus ready: {len(canonical)} documents.")


if __name__ == "__main__":
    main()
