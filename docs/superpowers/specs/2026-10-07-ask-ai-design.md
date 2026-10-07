# Ask AI Design Spec

Date: 2026-10-07
Status: Implemented; documented retrospectively from the code and tests. This document was not a pre-implementation approval artifact.
Source: User request to enable Ask AI with the OpenAI API and `gpt-4o-mini`, followed by approval to implement the chat plan.

## Purpose and scope

Let Campaign Pulse users ask natural-language questions about the currently filtered campaign dataset. Success means answers reference supplied campaign metrics and dates, support follow-up questions, and explain when available data cannot answer a question. The existing AI Insights tab remains rule-based.

This feature uses summaries rather than arbitrary data querying. It does not execute generated code, modify campaigns, browse the web, or send the original CSV to OpenAI. Suggestions are model-generated recommendations, not established causal explanations.

## Architecture and interfaces

`app.py` owns credentials resolution, chat display, submission, loading feedback and session state. `campaign_pulse/query.py` builds campaign context and makes server-side OpenAI Responses API requests. Existing `metrics.py` supplies ratios of sums and `data.py` supplies the allowed numeric fields.

```text
CSV or generated sample -> existing validation -> sidebar filters
  -> build_context(filtered, source) -> JSON summaries
  -> ask(question, context, history, api_key=..., model=...)
  -> OpenAI Responses API -> text answer -> session chat
```

- `build_context(df: pd.DataFrame, source: str, max_rows: int = 100) -> str`: produces JSON containing source, selected row count, date range, available fields, totals, platform breakdown, platform/campaign breakdown and daily breakdown. Empty input raises `QueryError`.
- `ask(question: str, context: str, history: list[dict], *, api_key: str = '', model: str | None = None, client=None) -> str`: returns nonempty answer text or raises a display-safe `QueryError`. Injectable clients allow transport-level tests without live calls.
- `render_ask_ai(filtered: pd.DataFrame, source: str, scope: str) -> None`: renders the tab and controls successful conversation updates.

## Global constraints

- Python `>=3.10`; Streamlit `>=1.30.0`; Pandas `>=2.0.0`; OpenAI SDK `>=3.26.0`; package manager `uv`.
- Default model: `gpt-4o-mini`.
- Credentials remain server-side; never commit or log API keys.
- Metrics are ratios of sums, never means of row ratios.
- Each breakdown includes at most 100 rows by default; platform and campaign labels are limited to 200 characters.
- Questions are limited to 2,000 characters; retain at most six conversation messages and transmit at most 4,000 characters per history message.
- Responses are capped at 1,000 output tokens; SDK timeout is 30 seconds with one retry for eligible transient errors.
- Set `store=False` on Responses API requests. This is not a zero-retention guarantee.

## Data correctness and bounds

Totals include all filtered rows. Platform and campaign groups are ordered by spend descending; daily groups are ordered by date ascending. Each breakdown reports how many groups were omitted. Consequently, questions about omitted campaigns or later dates in a long range may not be answerable from supplied detail. This is a row and label bound, not a fixed token budget.

Unknown CSV columns are excluded. Campaign/platform names remain part of the transmitted summaries. Source is identified as uploaded data or generated sample data.

CPC = Spend/Clicks; CPA = Spend/Conversions; ROAS = Revenue/Spend; ROI = (Revenue-Spend)/Spend; CTR = Clicks/Impressions. Missing or undefined ratios serialize as JSON null. If an optional field has any missing values within a group, its group total is unavailable; CTR is unavailable when impressions coverage is incomplete. Missing impressions anywhere in the selection also make total CTR unavailable. These checks apply to Ask AI context; they do not change the other dashboard tabs.

## Credentials and model configuration

In the UI, environment values take precedence over top-level Streamlit secrets. `OPENAI_MODEL` defaults to `gpt-4o-mini`; `OPENAI_API_KEY` must be configured to enable input. The lower-level `ask` function accepts explicit settings, then falls back to environment settings.

```toml
# .streamlit/secrets.toml (excluded from Git)
OPENAI_API_KEY = "<new-api-key>"
OPENAI_MODEL = "gpt-4o-mini"
```

Alternatively, set the two variables in the server environment. No real credential is recorded here. Rotate keys previously exposed in chat before configuring them. Model identifiers are passed through to the SDK; invalid model configuration is surfaced as a safe API error.

## Conversation lifecycle

The tab shows example questions and disclosure that summaries and questions are sent to OpenAI. A missing key displays configuration instructions and disables input. Submission triggers one request with a spinner. Ordinary reruns render stored messages without submitting another request.

A SHA-256 fingerprint covers uploaded-file identity (or sample identity), filter widget selections and generated context. When it changes, history resets. An empty filtered result clears history before the app stops. Clear conversation also empties history. Successful user/assistant pairs are retained in session state, limited to six messages. Failed requests display an error and do not append a pair; users can resubmit. No chat database is used.

## Prompt and error handling

Instructions ask the model to use supplied data, explain unavailable values, distinguish recommendations from observations, label sample data, disclose relevant omissions and avoid invented causal claims. Names and user text are treated as untrusted data in the prompt. These instructions guide model behavior and do not guarantee answer correctness.

Authentication failures ask users to check credentials; rate/quota failures ask them to check billing or retry later; connection/timeouts and other API failures show concise recovery guidance. Raw provider error details are not displayed. Empty answers and blank/oversized questions raise safe errors. Retry and timeout behavior come from the OpenAI SDK; the timeout is not a total wall-clock deadline across retries.

## Validation and limitations

`tests/test_query.py` verifies weighted and filtered metrics, bounded context, missing ratios, exclusion of unknown columns, history/request parameters, safe provider errors, validation, timeout mapping, empty answers and incomplete optional fields. `tests/test_app.py` verifies missing-key behavior, chat submission, duplicate prevention, filter resets, empty-filter resets and recoverable API errors. HTTP transports are mocked while request construction and SDK response parsing remain real.

Live account access, model availability, billing and answer quality have not been verified with a configured key. Separate manual checks should cover secrets-only deployment configuration, uploaded-file replacement, Clear conversation, every filter control and large-data answer quality. Automated tests do not prove prompt-injection resistance or factual fidelity of model-generated prose.

See [implementation and verification record](../plans/2026-10-07-ask-ai.md) and [setup instructions](../../../README.md#ask-ai).
