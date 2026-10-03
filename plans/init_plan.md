# Project Plan: Inflation Mindshare in Fed Speeches

## Goal
Build a reproducible pipeline that measures the "mindshare" of inflation in Federal Reserve speeches using keyword frequency analysis.  
This project demonstrates systematic macro signal extraction with lightweight NLP, using **FedTools** as the data source.

## Key Steps
1. **Data Collection (FedTools)**
   - Use `fedtools` to download beigebook, statements and minutes from 2000-01-01.
   - Scrape the Federal Reserve website for speeches https://www.federalreserve.gov/newsevents/speeches-testimony.htm
   - Save raw text and metadata (date, source_type, title, speaker, text) into a parquet file 'data/Fed_df.parquet'

2. **Preprocessing**
   - Clean text (lowercase, remove punctuation).
   - Tokenize words.
   - Save processed text into `data/processed/`.

3. **Keyword Dictionary**
   - Define inflation-related keywords (e.g., "inflation", "price stability", "wage growth").
   - Define growth-related keywords (e.g. "recession", "expansion", "financial stability").
   - Define unemployment-related keywords (e.g. "unemployment", "jobless", "nonfarm payrolls").
   - Store dictionary in `src/keywords.py`.

4. **Mindshare Calculation**
   - Count keyword occurrences per text.
   - Normalize by inflation / (inflation + growth + unemployment) related word-count.
   - Aggregate results by time period or speaker.

5. **Visualization**
   - Plot inflation keyword intensity over time.
   - Compare across Fed chairs.
   - Save plots in `results/figures/`.

6. **Repo Structure**
   - `data/` → raw and processed speeches
   - `notebooks/` → step-by-step Jupyter notebooks
   - `src/` → modular Python scripts (data_loader, preprocessing, analysis, visualization)
   - `results/` → figures and metrics
   - `requirements.txt` → dependencies (`fedtools`, `pandas`, `matplotlib`, `spaCy`)
   - `README.md` → project overview

## Deliverables
- Modular Python code with docstrings.
- Jupyter notebooks for reproducibility.
- Clear README with methodology, results, and extensions.
- Example plots showing inflation mindshare trends.

## Constraints
- Use only free/public data via **FedTools**.
- Keep dependencies lightweight.
- Ensure code is easy to run on CPU.
