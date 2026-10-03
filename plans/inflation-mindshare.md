# Plan: Inflation Mindshare for Federal Reserve Communication

> Source PRD: [plans/init_plan.md](plans/init_plan.md)

## Architectural decisions

Durable decisions that apply across all phases:

- **Routes**: The project is a data pipeline rather than a web app. Execution is driven by command-line or notebook entry points, with a single end-to-end flow: ingest → normalize → score → aggregate → validate → visualize.
- **Schema**: A canonical document table stores document identifier, source type, date, title, speaker, chair, raw text, cleaned text, and derived topic counts. The daily series stores date, document count, topic counts, inflation mindshare, and validity flags.
- **Key models**: `DocumentRecord`, `TopicCounts`, `DailySeries`, `ValidationSummary`.
- **Third-party boundaries**: `fedtools` is the primary data provider for Fed documents, with selected scraping from the Federal Reserve speeches archive for authored speeches and testimony. No production API is required; all processing is local and reproducible.
- **Authentication / authorization**: Not applicable; the project uses public documents only and a local offline pipeline.

---

## Phase 1: Source coverage audit and publication checks

**User stories**: 1, 23, 24

### What to build

Audit the scraped corpus before scoring so the project can confirm there are no large missing gaps by `source_type`. This slice builds a yearly count of publications by document source and flags any abrupt drops or widespread absences that would otherwise distort the pooled series.

### Acceptance criteria

- [ ] A yearly count table is created for each `source_type` across the full analysis window.
- [ ] Large gaps or abrupt declines in source-type coverage are identified and reviewed before modeling.
- [ ] Any material collection failure is documented or corrected before the corpus is treated as complete.

---

## Phase 2: Canonical corpus and ingestion

**User stories**: 1, 2, 3, 4, 5, 23, 24, 25, 26

### What to build

Establish the data collection pipeline and a single canonical corpus that captures all relevant Federal Reserve communication from 2000 onward. This slice includes collecting Beige Books, statements, minutes, and authored speeches/testimony, normalizing records into one underlying schema, and making the publication date the governing date for the analysis.

### Acceptance criteria

- [x] A single document corpus includes all relevant Fed document types from 2000 onward.
- [x] All speeches are ingested, including records with incomplete metadata.
- [x] Each source type contributes equally in the pooled dataset at the document level rather than by volume dominance.
- [x] If a speech has no clear author, it is flagged for review and its URL is printed for manual inspection rather than silently excluded.
- [x] The document date reflects the publication or release date, and the corpus retains the metadata needed for later aggregation and chair comparison without mixing incompatible schemas.

---

## Phase 3: Text normalization and topic matching

**User stories**: 6, 7, 8, 9, 10, 18, 29

### What to build

Create the text-processing and topic-classification layer that turns raw documents into analyzable, category-labeled content. This slice covers lowercase normalization, punctuation cleanup, lemmatization, longest-match phrase matching, and exclusive category assignment to inflation, growth, and unemployment categories.

### Acceptance criteria

- [ ] Text normalization produces stable, reproducible tokens for keyword matching.
- [ ] Lemmatisation is applied before category matching so morphology does not break phrase detection.
- [ ] Longest-match rules prevent shorter generic terms from overshadowing more specific phrases.
- [ ] Each relevant keyword or phrase is counted once per document in the assigned category, without double counting within the same category.
- [ ] Ambiguous or overlapping matches are resolved with an exclusive assignment rule.

---

## Phase 4: Daily series, smoothing, and coverage rules

**User stories**: 11, 12, 13, 14, 15, 17, 19, 20, 21, 22, 27

### What to build

Build the core analytical output: a daily time series of inflation mindshare based on the pooled corpus, with coverage rules designed to prevent spurious readings. This slice produces the share metric, applies a trailing 3-month smoothing window, excludes sparse periods, and preserves missing dates when no documents are available.

### Acceptance criteria

- [ ] Daily aggregation uses available documents from each date and keeps genuinely empty dates as missing rather than zero-filled.
- [ ] The inflation share is computed as inflation-related content divided by inflation + growth + unemployment content.
- [ ] The time series supports a trailing 3-month moving average with clear handling of missing observations.
- [ ] Periods with fewer than 10 observed documents are treated as missing rather than analyzed.
- [ ] The resulting metric is available in aggregate form and supports chair-level comparison where metadata exists.

---

## Phase 5: Validation, quality gates, and demonstration outputs

**User stories**: 15, 16, 17, 18, 24, 25, 26, 27, 28

### What to build

Add the lightweight validation layer and presentation outputs required to make the project credible and reproducible. This includes manual review of a small labeled sample, precision and recall checks for each category, exclusion of weak categories, and final plots plus documentation that explain how the metric is produced and interpreted.

### Acceptance criteria

- [ ] A validation sample is created for manual annotation and compared against automated labels.
- [ ] Each category meets the minimum validation threshold of 80% precision and 80% recall before being trusted for use.
- [ ] Categories that fail validation are revised or excluded rather than silently included.
- [ ] The project produces reproducible figures and summary documentation showing the inflation mindshare time series and supporting methodology.
- [ ] The repository remains organized around data, notebooks, source, and results so the pipeline is easy to run and extend.

---

## Phase 6: Hardening and release-readiness

**User stories**: 24, 25, 26, 28

### What to build

Finalize the project as a small, maintainable research pipeline with clear operational boundaries. This slice focuses on ensuring the code is modular, tests are focused on external behavior, and the documentation explains the rules and caveats so future contributors can extend the project safely.

### Acceptance criteria

- [ ] Core pipeline stages are isolated and easy to run independently.
- [ ] Tests cover ingestion, preprocessing, category assignment, aggregation, and validation logic using realistic fixtures.
- [ ] Documentation describes the dataset, method, assumptions, and validation thresholds without overstating the scope of the analysis.
- [ ] The project is demonstrably executable on a standard CPU setup with lightweight dependencies.
