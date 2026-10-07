"""Campaign Pulse: ad campaign performance dashboard."""
import hashlib
import os

import pandas as pd
import streamlit as st

from campaign_pulse import charts, data, filters, insights, metrics, query

st.set_page_config(page_title="Campaign Pulse", page_icon="📈", layout="wide")


@st.cache_data(show_spinner=False)
def load_upload(raw: bytes) -> tuple[pd.DataFrame, int]:
    return data.parse_csv(raw)


@st.cache_data(show_spinner=False)
def load_fallback() -> tuple[pd.DataFrame, int]:
    return data.generate_fallback(), 0


def load_data() -> tuple[pd.DataFrame, int]:
    st.sidebar.header("Data")
    upload = st.sidebar.file_uploader("Upload campaign CSV", type="csv", key="campaign_upload")
    st.sidebar.download_button("Download CSV template", data.template_csv(), "campaign_template.csv", "text/csv")
    if upload is None:
        st.sidebar.info("No file uploaded: showing a generated 30-day sample.")
        return load_fallback()
    try:
        return load_upload(upload.getvalue())
    except data.SchemaError as exc:
        st.error(f"Missing required columns: {', '.join(exc.missing)}. Download the CSV template in the sidebar for the expected format.")
    except data.DataError as exc:
        st.error(str(exc))
    st.stop()


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    min_date, max_date = df["Date"].min(), df["Date"].max()

    preset = st.sidebar.selectbox("Date range", filters.PRESETS, index=1, key="date_preset")
    if preset == "Custom":
        picked = st.sidebar.date_input(
            "Custom range", value=(min_date.date(), max_date.date()),
            min_value=min_date.date(), max_value=max_date.date(), key="custom_range",
        )
        if isinstance(picked, (tuple, list)) and not picked:
            start, end = min_date, max_date
        else:
            start, end = filters.normalize_range(picked)
    else:
        start, end = filters.preset_range(preset, min_date, max_date)

    platform_options = sorted(df["Platform"].unique())
    platforms = st.sidebar.multiselect("Platform", platform_options, default=platform_options, key="platform_filter")

    campaign_options = filters.campaigns_for(df, platforms)
    campaigns = st.sidebar.multiselect(
        "Campaign", campaign_options, default=campaign_options, key="campaigns-" + "|".join(platforms)
    )

    top_spend = float(df["Spend"].max())
    min_spend = 0.0
    if top_spend > 0:
        min_spend = st.sidebar.slider("Minimum spend per row", 0.0, top_spend, 0.0, step=max(top_spend / 100, 0.01), key="min_spend_filter")

    st.sidebar.caption(f"Showing {start:%b %d, %Y} to {end:%b %d, %Y}")
    return filters.apply_filters(df, start, end, platforms, campaigns, min_spend)


def render_overview(filtered: pd.DataFrame) -> None:
    s = metrics.summarize(filtered)
    cards = [
        ("Total Spend", metrics.money(s["Spend"])),
        ("Total Revenue", metrics.money(s["Revenue"])),
        ("ROAS", metrics.multiple(s["ROAS"])),
        ("Avg CPA", metrics.money(s["CPA"])),
        ("Avg CPC", metrics.money(s["CPC"])),
        ("Conversions", metrics.count(s['Conversions'])),
    ]
    for col, (label, value) in zip(st.columns(6), cards):
        col.metric(label, value)

    if "CTR" in s:
        st.caption(f"CTR: {metrics.pct(s['CTR'])}")
    else:
        st.caption("CTR unavailable: add an Impressions column to your CSV.")

    table = metrics.add_metrics(filtered)
    st.dataframe(table)
    st.download_button("Download filtered CSV", table.to_csv(index=False).encode("utf-8"), "campaign_filtered.csv", "text/csv")


def render_platforms(filtered: pd.DataFrame) -> None:
    left, right = st.columns(2)
    left.plotly_chart(charts.platform_spend_revenue(filtered))
    right.plotly_chart(charts.platform_cpa(filtered))
    st.plotly_chart(charts.funnel_figure(filtered))
    if "Landing Page Visits" not in filtered.columns:
        st.caption("Landing Page Visits not found: funnel shows Clicks to Conversions only.")


def render_trends(filtered: pd.DataFrame) -> None:
    metric = st.selectbox("Metric", charts.METRIC_OPTIONS)
    moving_average = st.checkbox("7-Day Moving Average")
    st.plotly_chart(charts.trend_figure(filtered, metric, moving_average))


def render_insights(filtered: pd.DataFrame) -> None:
    for item in insights.generate_insights(filtered):
        getattr(st, item.level)(item.text)


def render_ask_ai(filtered: pd.DataFrame, source: str, scope: str) -> None:
    st.subheader("Ask AI")
    st.caption("Ask about the current filtered campaign data. Campaign summaries and your questions are sent to OpenAI.")
    st.caption("Try: Which campaign has the highest ROAS? How did spend change over this period?")
    context = query.build_context(filtered, source)
    fingerprint = hashlib.sha256((scope + context).encode()).hexdigest()
    if st.session_state.get("ask_ai_scope") != fingerprint:
        st.session_state.ask_ai_scope = fingerprint
        st.session_state.ask_ai_messages = []
    if st.button("Clear conversation", key="clear_ask_ai"):
        st.session_state.ask_ai_messages = []

    def setting(name: str, default: str = "") -> str:
        value = os.getenv(name)
        if value is not None:
            return value
        try:
            return str(st.secrets.get(name, default))
        except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
            return default

    api_key = setting("OPENAI_API_KEY")
    model = setting("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        st.info("Configure OPENAI_API_KEY in the server environment or .streamlit/secrets.toml to enable Ask AI.")
    messages = st.session_state.ask_ai_messages
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Ask about your campaigns", disabled=not bool(api_key),
                             max_chars=query.MAX_QUESTION, key="ask_ai_question")
    if question:
        try:
            with st.spinner("Analyzing campaign data…"):
                answer = query.ask(question, context, messages, api_key=api_key, model=model)
        except query.QueryError as exc:
            st.error(str(exc))
            return
        messages.extend([{"role": "user", "content": question},
                         {"role": "assistant", "content": answer}])
        st.session_state.ask_ai_messages = messages[-query.MAX_HISTORY:]
        for role, content in (("user", question), ("assistant", answer)):
            with st.chat_message(role):
                st.markdown(content)


def main() -> None:
    df, dropped = load_data()
    if dropped:
        st.sidebar.warning(f"{dropped} invalid row(s) were skipped.")

    st.title("Campaign Pulse")
    filtered = sidebar_filters(df)
    if filtered.empty:
        st.session_state.ask_ai_messages = []
        st.session_state.ask_ai_scope = None
        st.warning("No rows match the current filters. Widen the date range, select more platforms or campaigns, or lower the minimum spend.")
        st.stop()

    overview, platforms, trends, ai_insights, ask_ai = st.tabs(
        ["Overview", "Platform & Funnels", "Trends", "AI Insights", "Ask AI"]
    )
    with overview:
        render_overview(filtered)
    with platforms:
        render_platforms(filtered)
    with trends:
        render_trends(filtered)
    with ai_insights:
        render_insights(filtered)
    with ask_ai:
        upload = st.session_state.get("campaign_upload")
        source = "uploaded" if upload is not None else "generated sample"
        identity = hashlib.sha256(upload.getvalue()).hexdigest() if upload is not None else "sample"
        selection = repr([widget for widget in (st.session_state.get("date_preset"),
                         st.session_state.get("custom_range"), st.session_state.get("platform_filter"),
                         st.session_state.get("min_spend_filter"),
                         st.session_state.get("campaigns-" + "|".join(st.session_state.get("platform_filter", []))))])
        render_ask_ai(filtered, source, identity + selection)


main()
