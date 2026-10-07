"""Loading, validating and generating campaign data."""
from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd

REQUIRED = ["Date", "Platform", "Campaign", "Spend", "Clicks", "Conversions", "Revenue"]
OPTIONAL = ["Impressions", "Landing Page Visits"]
_REQUIRED_NUMERIC = ["Spend", "Clicks", "Conversions", "Revenue"]
NUMERIC_COLUMNS = _REQUIRED_NUMERIC + OPTIONAL

_ALIASES = {
    "date": "Date", "day": "Date", "reportingdate": "Date",
    "platform": "Platform", "channel": "Platform", "source": "Platform",
    "campaign": "Campaign", "campaignname": "Campaign",
    "spend": "Spend", "cost": "Spend", "adspend": "Spend",
    "clicks": "Clicks", "click": "Clicks",
    "conversions": "Conversions", "conversion": "Conversions", "conv": "Conversions",
    "revenue": "Revenue", "sales": "Revenue", "conversionvalue": "Revenue",
    "impressions": "Impressions", "impression": "Impressions", "impr": "Impressions",
    "landingpagevisits": "Landing Page Visits", "lpvisits": "Landing Page Visits",
    "landingpageviews": "Landing Page Visits",
}

_PROFILES = {
    # platform: (campaign, base daily spend, cost per click, CTR, click->conversion rate, avg order value)
    "Google": ("Search_Brand", 130, 0.35, 0.040, 0.050, 38),
    "Meta": ("Retargeting_V1", 220, 0.40, 0.020, 0.045, 30),
    "LinkedIn": ("B2B_Outreach", 350, 1.90, 0.008, 0.035, 150),
}


class DataError(ValueError):
    """The uploaded data cannot be used."""


class SchemaError(DataError):
    """Required columns are missing."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing required columns: {', '.join(missing)}")


def _key(name: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename recognised header variants to canonical names; keep unknown columns."""
    renamed = df.rename(columns=lambda c: _ALIASES.get(_key(c), str(c).strip()))
    return renamed.loc[:, ~renamed.columns.duplicated()]


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Validate and coerce a raw frame. Returns (clean frame, rows dropped)."""
    df = normalize_columns(df)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SchemaError(missing)

    df = df[REQUIRED + [c for c in OPTIONAL if c in df.columns]].copy()
    before = len(df)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", format="mixed").dt.normalize()
    for col in NUMERIC_COLUMNS:
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].astype(str).str.replace(r"[$€£,\s]", "", regex=True)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("Platform", "Campaign"):
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["Date", *_REQUIRED_NUMERIC])
    df = df[(df[_REQUIRED_NUMERIC] >= 0).all(axis=1)]
    df = df[~df["Platform"].str.lower().isin(["", "nan"])]
    if df.empty:
        raise DataError("No valid rows found. Check dates and that numeric columns contain numbers.")

    df = df.sort_values(["Date", "Platform"]).reset_index(drop=True)
    return df, before - len(df)


def parse_csv(raw: bytes) -> tuple[pd.DataFrame, int]:
    """Parse uploaded CSV bytes into a clean frame. Raises DataError on bad input."""
    try:
        df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DataError(f"Could not read the file as CSV: {exc}") from exc
    return clean(df)


def generate_fallback(
    days: int = 30, seed: int = 42, end: str | pd.Timestamp | None = None
) -> pd.DataFrame:
    """Deterministic demo data: one campaign per platform, one row per day."""
    rng = np.random.default_rng(seed)
    end_ts = pd.Timestamp(end).normalize() if end is not None else pd.Timestamp.today().normalize()
    rows = []
    for day in pd.date_range(end=end_ts, periods=days):
        for platform, (campaign, base, cpc, ctr, cvr, aov) in _PROFILES.items():
            spend = round(base * rng.uniform(0.85, 1.15), 2)
            clicks = int(round(spend / cpc * rng.uniform(0.9, 1.1)))
            impressions = int(round(clicks / ctr * rng.uniform(0.9, 1.1)))
            visits = int(round(clicks * rng.uniform(0.75, 0.9)))
            conversions = min(int(round(clicks * cvr * rng.uniform(0.8, 1.2))), visits)
            revenue = round(conversions * aov * rng.uniform(0.85, 1.15), 2)
            rows.append(
                {
                    "Date": day, "Platform": platform, "Campaign": campaign, "Spend": spend,
                    "Impressions": impressions, "Clicks": clicks, "Landing Page Visits": visits,
                    "Conversions": conversions, "Revenue": revenue,
                }
            )
    return pd.DataFrame(rows)


def template_csv() -> str:
    """A downloadable example showing the expected columns."""
    return (
        "Date,Platform,Campaign,Spend,Clicks,Conversions,Revenue,Impressions,Landing Page Visits\n"
        "2026-01-01,Google,Search_Brand,120.50,350,15,450.00,9000,300\n"
    )
