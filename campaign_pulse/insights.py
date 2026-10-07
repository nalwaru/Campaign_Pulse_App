"""Rule-based executive insights (Story 4.1)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from campaign_pulse.metrics import by_platform, money, multiple


@dataclass(frozen=True)
class Insight:
    level: str  # "success" | "warning" | "info"
    text: str


def generate_insights(df: pd.DataFrame) -> list[Insight]:
    if df.empty:
        return [Insight("info", "No data matches the current filters.")]

    plat = by_platform(df)
    if len(plat) < 2:
        name = plat["Platform"].iloc[0]
        return [Insight("info", f"Only {name} is in the current selection. Select two or more platforms to compare efficiency.")]

    out: list[Insight] = []

    best = None
    with_roas = plat.dropna(subset=["ROAS"])
    if not with_roas.empty:
        best = with_roas.loc[with_roas["ROAS"].idxmax()]
        out.append(
            Insight(
                "success",
                f"Top performer: {best['Platform']} returns {multiple(best['ROAS'])} ROAS "
                f"({money(best['Revenue'])} revenue on {money(best['Spend'])} spend).",
            )
        )

    worst = None
    dead = plat[(plat["Conversions"] == 0) & (plat["Spend"] > 0)]
    if not dead.empty:
        worst = dead.loc[dead["Spend"].idxmax()]
        for _, row in dead.iterrows():
            out.append(Insight("warning", f"{row['Platform']} spent {money(row['Spend'])} with no conversions."))
    else:
        with_cpa = plat.dropna(subset=["CPA"])
        if len(with_cpa) >= 2 and with_cpa["CPA"].max() != with_cpa["CPA"].min():
            worst = with_cpa.loc[with_cpa["CPA"].idxmax()]
            out.append(
                Insight("warning", f"Least efficient: {worst['Platform']} has the highest CPA at {money(worst['CPA'])}.")
            )

    if best is not None and worst is not None and best["Platform"] != worst["Platform"]:
        out.append(
            Insight(
                "info",
                f"Budget opportunity: consider shifting spend from {worst['Platform']} "
                f"to {best['Platform']} (ROAS {multiple(best['ROAS'])} vs {multiple(worst['ROAS'])}; "
                f"{worst['Platform']} CPA {money(worst['CPA'])}). "
                f"Validate with a small test before moving large budgets.",
            )
        )

    return out or [Insight("info", "Not enough data to generate insights for this selection.")]
