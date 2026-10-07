# Campaign Pulse

Streamlit dashboard for ad campaign performance (Spend, Revenue, Conversions, CTR, CPC, CPA, ROAS, ROI).

## Setup

```bash
uv sync
uv run streamlit run app.py   # http://localhost:8501
uv run pytest                 # run tests
```

## CSV format

Required columns: `Date, Platform, Campaign, Spend, Clicks, Conversions, Revenue`.
Optional: `Impressions` (enables CTR), `Landing Page Visits` (adds a funnel step).
Common header variants (`Cost`, `Channel`, `Conv.`, `Impr.`, ...) are recognised.
A template is downloadable from the sidebar; `sample_data/campaign_sample.csv` is a working example.
Dates are read with one format for the whole file: ISO (`2026-01-31`), `MM/DD/YYYY`, `DD/MM/YYYY`,
`DD.MM.YYYY` or `DD-MM-YYYY`, whichever fits the most rows. If a slash-date file is ambiguous
(every first number is 12 or less) it is read month-first (US). Rows that do not fit are dropped and counted.
Files must be comma-separated (UTF-8 or Excel's default Windows encoding).
With no upload the app shows a generated 30-day dataset.

## Metrics

All ratios are computed from sums: CPC = Spend/Clicks, CPA = Spend/Conversions, ROAS = Revenue/Spend,
ROI = (Revenue - Spend)/Spend, CTR = Clicks/Impressions. A zero denominator shows `-`.

## Roadmap

- "Ask AI" natural-language queries (Story 4.2) is parked pending a design decision.
