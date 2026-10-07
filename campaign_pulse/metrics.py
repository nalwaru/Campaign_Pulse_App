"""Derived campaign metrics. All ratios are computed from sums."""
from __future__ import annotations

import pandas as pd

from campaign_pulse.data import NUMERIC_COLUMNS


def safe_div(num, den):
    """Divide, returning NaN instead of inf for a zero denominator."""
    if isinstance(den, pd.Series):
        return num / den.where(den != 0)
    return num / den if den else float("nan")


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["CPC"] = safe_div(out["Spend"], out["Clicks"])
    out["CPA"] = safe_div(out["Spend"], out["Conversions"])
    out["ROAS"] = safe_div(out["Revenue"], out["Spend"])
    out["ROI"] = safe_div(out["Revenue"] - out["Spend"], out["Spend"])
    if "Impressions" in out.columns:
        out["CTR"] = safe_div(out["Clicks"], out["Impressions"])
    return out


def summarize(df: pd.DataFrame) -> dict[str, float]:
    spend = float(df["Spend"].sum())
    revenue = float(df["Revenue"].sum())
    clicks = float(df["Clicks"].sum())
    conversions = float(df["Conversions"].sum())
    out = {
        "Spend": spend,
        "Revenue": revenue,
        "Clicks": clicks,
        "Conversions": conversions,
        "CPC": safe_div(spend, clicks),
        "CPA": safe_div(spend, conversions),
        "ROAS": safe_div(revenue, spend),
        "ROI": safe_div(revenue - spend, spend),
    }
    if "Impressions" in df.columns:
        out["CTR"] = safe_div(clicks, float(df["Impressions"].sum()))
    return out


def by_platform(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in NUMERIC_COLUMNS if c in df.columns]
    return add_metrics(df.groupby("Platform", as_index=False)[cols].sum())


def money(value: float) -> str:
    return "-" if pd.isna(value) else f"${value:,.2f}"


def multiple(value: float) -> str:
    return "-" if pd.isna(value) else f"{value:.2f}x"


def pct(value: float) -> str:
    return "-" if pd.isna(value) else f"{value:.2%}"
