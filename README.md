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

## Ask AI

Ask AI answers questions about the currently filtered campaign dataset using OpenAI.
Python calculates weighted metrics; OpenAI receives bounded totals, platform/campaign
breakdowns and daily trends, plus your question and recent conversation. Unknown CSV
columns and the original CSV file are not sent. Each breakdown includes at most 100
rows; omitted counts are supplied to the model. Names are limited to 200 characters.
Answers may have limitations when details are omitted and should be checked against
the dashboard. The existing AI Insights tab continues to use local rules.

Set server environment variables before starting the app:

```bash
export OPENAI_API_KEY="<your-new-api-key>"
export OPENAI_MODEL="gpt-4o-mini"
uv run streamlit run app.py
```

Alternatively, create `.streamlit/secrets.toml` (already excluded from Git):

```toml
OPENAI_API_KEY = "<your-new-api-key>"
OPENAI_MODEL = "gpt-4o-mini"
```

Environment values take precedence over Streamlit secrets. The model defaults to
`gpt-4o-mini`. Never put credentials in `pyproject.toml` or commit them. Rotate any
key previously shared in a conversation.

Try “Which campaign has the highest ROAS?” or “How did spend change over this period?”
History is session-only and clears on dataset/filter changes or with Clear conversation.
Questions are limited to 2,000 characters, the last six chat messages are retained,
and responses are capped at 1,000 output tokens. Requests have a 30-second timeout
per attempt and one SDK retry for transient errors. API responses use `store=False`;
this disables response storage, but does not imply zero retention of API data.
OpenAI API usage is billed to the configured project. No request is made until a
question is submitted. Without a key, Ask AI displays setup instructions.

Design and implementation records: [Ask AI spec](docs/superpowers/specs/2026-10-07-ask-ai-design.md) and [Ask AI plan](docs/superpowers/plans/2026-10-07-ask-ai.md).
