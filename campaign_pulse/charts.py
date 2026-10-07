"""Plotly figure builders. Pure functions: DataFrame in, Figure out."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from campaign_pulse.data import NUMERIC_COLUMNS
from campaign_pulse.metrics import add_metrics, by_platform

METRIC_OPTIONS = ["Revenue", "Spend", "Conversions", "ROAS"]


def platform_spend_revenue(df: pd.DataFrame) -> go.Figure:
    long = by_platform(df).melt(
        id_vars="Platform", value_vars=["Spend", "Revenue"], var_name="Metric", value_name="Amount"
    )
    fig = px.bar(long, x="Platform", y="Amount", color="Metric", barmode="group", title="Spend vs Revenue by Platform")
    fig.update_yaxes(tickprefix="$")
    return fig


def platform_cpa(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(by_platform(df), x="Platform", y="CPA", title="CPA by Platform")
    fig.update_yaxes(tickprefix="$")
    return fig


def funnel_figure(df: pd.DataFrame) -> go.Figure:
    stages = [("Clicks", df["Clicks"].sum())]
    if "Landing Page Visits" in df.columns:
        stages.append(("Landing Page Visits", df["Landing Page Visits"].sum()))
    stages.append(("Conversions", df["Conversions"].sum()))
    frame = pd.DataFrame(stages, columns=["Stage", "Count"])
    return px.funnel(frame, x="Count", y="Stage", title="Conversion Funnel")


def trend_figure(df: pd.DataFrame, metric: str, moving_average: bool) -> go.Figure:
    cols = [c for c in NUMERIC_COLUMNS if c in df.columns]
    daily = add_metrics(df.groupby(["Date", "Platform"], as_index=False)[cols].sum()).sort_values("Date")
    fig = px.line(daily, x="Date", y=metric, color="Platform", markers=True, title=f"Daily {metric} by Platform")
    if moving_average:
        for platform, group in daily.groupby("Platform"):
            rolling = group.set_index("Date")[metric].rolling("7D", min_periods=1).mean()
            fig.add_trace(
                go.Scatter(
                    x=rolling.index, y=rolling.values, mode="lines",
                    name=f"{platform} 7-day avg", line={"dash": "dash"},
                )
            )
    return fig
