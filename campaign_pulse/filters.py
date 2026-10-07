"""Sidebar filter logic, kept free of Streamlit."""
from __future__ import annotations

import pandas as pd

PRESETS = ["Last 7 Days", "Last 30 Days", "Custom"]
_PRESET_DAYS = {"Last 7 Days": 7, "Last 30 Days": 30}


def preset_range(preset: str, min_date: pd.Timestamp, max_date: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Date window for a preset, anchored to the latest date in the data."""
    days = _PRESET_DAYS.get(preset)
    if days is None:
        return min_date, max_date
    return max(max_date - pd.Timedelta(days=days - 1), min_date), max_date


def normalize_range(value) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Coerce st.date_input output (date, or 1/2-item tuple) to a Timestamp pair."""
    items = list(value) if isinstance(value, (tuple, list)) else [value]
    start = pd.Timestamp(items[0])
    end = pd.Timestamp(items[1]) if len(items) > 1 else start
    return start, end


def campaigns_for(df: pd.DataFrame, platforms: list[str]) -> list[str]:
    return sorted(df.loc[df["Platform"].isin(platforms), "Campaign"].unique())


def apply_filters(
    df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    platforms: list[str],
    campaigns: list[str],
    min_spend: float,
) -> pd.DataFrame:
    mask = (
        (df["Date"] >= pd.Timestamp(start))
        & (df["Date"] <= pd.Timestamp(end))
        & df["Platform"].isin(platforms)
        & df["Campaign"].isin(campaigns)
        & (df["Spend"] >= min_spend)
    )
    return df[mask]
