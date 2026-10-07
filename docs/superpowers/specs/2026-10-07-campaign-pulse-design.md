# Campaign Pulse App: Design Spec

Date: 2026-10-07
Source requirements: `campaign_req.pages` (4 epics, 8 stories). Sample data: `compaign_sheet.numbers`.

## Context
A Streamlit dashboard where marketers upload cross-platform ad CSVs (or use a generated 30-day fallback), filter them, and see KPIs, charts and rule-based insights. Python >=3.10, Streamlit >=1.30, Pandas >=2.0, Plotly >=5.18, managed with `uv`.

**Scope now:** Epics 1-3 + Story 4.1 (rule-based insights).
**Parked by user decision:** Story 4.2 "Ask AI". The app shows an "Ask AI" tab placeholder ("coming soon"). There is no `query.py` yet.

## Findings from the sample file
- Columns: `Date, Platform, Campaign, Spend, Clicks, Conversions, Revenue`. Daily rows, 3 platforms (Google, Meta, LinkedIn), one campaign each, dates from 2026-01-01.
- No Impressions, so CTR cannot be computed from this file.
- No Landing Page Visits, so the PRD funnel (Clicks -> LP Visits -> Conversions) cannot be built from this file.
- Dates are historical, so date presets anchor to the **max date in the data**, not today.

## Design decisions
- **Required columns:** Date, Platform, Campaign, Spend, Clicks, Conversions, Revenue. **Optional:** Impressions, Landing Page Visits.
- **CTR** is shown only when Impressions is present. Otherwise the card and column are omitted, with a caption explaining why.
- **Funnel:** Clicks -> (Landing Page Visits if present) -> Conversions.
- **Metrics** are ratios of sums, never a mean of row ratios:
  - CPC = Spend / Clicks
  - CPA = Spend / Conversions
  - ROAS = Revenue / Spend
  - ROI = (Revenue - Spend) / Spend
  - CTR = Clicks / Impressions
  - A zero denominator gives NaN, displayed as "-".
- **Aliasing:** case- and space-insensitive header map (e.g. `Cost` -> Spend, `Impr.` -> Impressions, `Conv.` -> Conversions, `Channel` -> Platform, `Day` -> Date).
- **Validation:** missing required columns -> `st.error` listing them plus a downloadable CSV template. Bad dates, non-numeric values and negatives are reported; affected rows are coerced or dropped, with a count shown.
- **Fallback data:** deterministic (seeded) 30-day dataset across 3 platforms. It uses the sample schema plus Impressions and Landing Page Visits so every feature can be demoed.
- **Caching:** `st.cache_data` on `load_csv(file_bytes)` and on the fallback generator.
- **Input format:** CSV only. Numbers files are not readable by Pandas, so the sample is exported to `sample_data/campaign_sample.csv`.

## Structure
```
Campaign_Pulse_App/
  pyproject.toml          # uv project; streamlit>=1.30, pandas>=2.0, plotly>=5.18; dev: pytest
  .python-version, .gitignore, README.md
  app.py                  # thin Streamlit entry: sidebar, tabs, wiring only
  campaign_pulse/
    data.py               # alias, validate, load_csv, fallback generator, template CSV
    metrics.py            # derived columns + aggregate KPIs (pure)
    filters.py            # date presets, platform/campaign/min-spend filtering (pure)
    charts.py             # Plotly figures: platform bars, funnel, time series (+7d MA)
    insights.py           # rule-based callouts (pure)
  tests/                  # pytest for data, metrics, filters, insights
  sample_data/            # campaign_sample.csv
  docs/superpowers/specs/ # this spec
  docs/superpowers/plans/ # implementation plan
```

## Story mapping
- **1.1 uv:** `uv sync` and `uv run streamlit run app.py` work on a fresh clone (serves on localhost:8501).
- **1.2 Ingestion:** sidebar `st.file_uploader`; with no file, the fallback dataset loads; derived metrics are computed on the fly.
- **2.1 Sidebar:** date preset selectbox (Last 7 Days / Last 30 Days / Custom range), platform and campaign multiselects (campaign options depend on the selected platforms), minimum-spend slider. One filtered DataFrame feeds every tab.
- **3.1 Overview tab:** 6 `st.metric` cards (Total Spend, Total Revenue, ROAS, Avg CPA, Avg CPC, Conversions), `st.dataframe`, and an `st.download_button` exporting the filtered data.
- **3.2 Platform & Funnels tab:** `px.bar` of Spend vs Revenue by platform, `px.bar` of CPA by platform, and `px.funnel`.
- **3.3 Trends tab:** metric selectbox (Revenue, Spend, Conversions, ROAS), `px.line` by platform, and a 7-day moving-average checkbox. The rolling mean runs over each platform's daily series, and ROAS is computed from daily sums.
- **4.1 AI Insights tab:** top platform by ROAS (`st.success`), least efficient platform by CPA (`st.warning`), and a budget recommendation (`st.info`) such as shifting spend from the worst-CPA platform to the best-ROAS platform. Empty or insufficient data is handled.
- **Edge cases:** an empty filter result shows a friendly message instead of crashing; single-platform data skips comparative insights.

## Verification
- `uv sync` on a clean clone succeeds, and `uv run pytest` passes.
- `uv run streamlit run app.py` serves at http://localhost:8501 and the fallback data loads.
- Uploading `sample_data/campaign_sample.csv`: the 6 KPIs match hand-computed totals, CTR is omitted, and the funnel is Clicks -> Conversions.
- Filters (presets, multiselects, min spend) work, the exported CSV matches the filtered view, and an invalid CSV shows the error and template.
- Visual check of all tabs in a browser.

## Open items
- Story 4.2 "Ask AI" is deferred. Revisit the approach later (rule-based, or optional Claude via `ANTHROPIC_API_KEY`).
