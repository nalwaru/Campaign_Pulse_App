"""Campaign Pulse: ad campaign performance dashboard."""
import pandas as pd
import streamlit as st

from campaign_pulse import charts, data, filters, insights, metrics

st.set_page_config(page_title="Campaign Pulse", page_icon="📈", layout="wide")


@st.cache_data(show_spinner=False)
def load_upload(raw: bytes) -> tuple[pd.DataFrame, int]:
    return data.parse_csv(raw)


@st.cache_data(show_spinner=False)
def load_fallback() -> tuple[pd.DataFrame, int]:
    return data.generate_fallback(), 0


def load_data() -> tuple[pd.DataFrame, int]:
    st.sidebar.header("Data")
    upload = st.sidebar.file_uploader("Upload campaign CSV", type="csv")
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

    preset = st.sidebar.selectbox("Date range", filters.PRESETS, index=1)
    if preset == "Custom":
        picked = st.sidebar.date_input(
            "Custom range", value=(min_date.date(), max_date.date()),
            min_value=min_date.date(), max_value=max_date.date(),
        )
        if isinstance(picked, (tuple, list)) and not picked:
            start, end = min_date, max_date
        else:
            start, end = filters.normalize_range(picked)
    else:
        start, end = filters.preset_range(preset, min_date, max_date)

    platform_options = sorted(df["Platform"].unique())
    platforms = st.sidebar.multiselect("Platform", platform_options, default=platform_options)

    campaign_options = filters.campaigns_for(df, platforms)
    campaigns = st.sidebar.multiselect(
        "Campaign", campaign_options, default=campaign_options, key="campaigns-" + "|".join(platforms)
    )

    top_spend = float(df["Spend"].max())
    min_spend = 0.0
    if top_spend > 0:
        min_spend = st.sidebar.slider("Minimum spend per row", 0.0, top_spend, 0.0, step=max(top_spend / 100, 0.01))

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
        ("Conversions", f"{int(s['Conversions']):,}"),
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


def main() -> None:
    df, dropped = load_data()
    if dropped:
        st.sidebar.warning(f"{dropped} invalid row(s) were skipped.")

    st.title("Campaign Pulse")
    filtered = sidebar_filters(df)
    if filtered.empty:
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
        st.info("Ask AI is coming soon.")


main()
