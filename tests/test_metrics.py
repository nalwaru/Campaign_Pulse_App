import math

import pandas as pd
import pytest

from campaign_pulse import metrics


def test_safe_div_scalar_and_series():
    assert math.isnan(metrics.safe_div(5, 0))
    assert metrics.safe_div(6, 3) == 2
    out = metrics.safe_div(pd.Series([1.0, 2.0]), pd.Series([0.0, 4.0]))
    assert math.isnan(out.iloc[0])
    assert out.iloc[1] == 0.5


def test_add_metrics_per_row(sample_df):
    out = metrics.add_metrics(sample_df)
    first = out.iloc[0]
    assert first["CPC"] == 1.0
    assert first["CPA"] == 10.0
    assert first["ROAS"] == 5.0
    assert first["ROI"] == 4.0
    assert "CTR" not in out.columns


def test_add_metrics_adds_ctr_when_impressions_present(sample_df):
    df = sample_df.assign(Impressions=[1000] * 6)
    assert metrics.add_metrics(df).iloc[0]["CTR"] == pytest.approx(0.1)


def test_summarize_uses_ratio_of_sums(sample_df):
    s = metrics.summarize(sample_df)
    assert s["Spend"] == 1200
    assert s["Revenue"] == 3400
    assert s["Conversions"] == 66
    assert s["ROAS"] == pytest.approx(3400 / 1200)
    assert s["CPA"] == pytest.approx(1200 / 66)
    assert s["CPC"] == pytest.approx(1200 / 800)
    assert s["ROI"] == pytest.approx((3400 - 1200) / 1200)
    assert "CTR" not in s


def test_summarize_zero_denominators_are_nan(sample_df):
    df = sample_df.assign(Clicks=0, Conversions=0, Spend=0.0)
    s = metrics.summarize(df)
    assert math.isnan(s["CPC"]) and math.isnan(s["CPA"]) and math.isnan(s["ROAS"]) and math.isnan(s["ROI"])


def test_summarize_empty_frame_does_not_crash(sample_df):
    s = metrics.summarize(sample_df.iloc[0:0])
    assert s["Spend"] == 0
    assert math.isnan(s["ROAS"])


def test_by_platform(sample_df):
    out = metrics.by_platform(sample_df).set_index("Platform")
    assert out.loc["Google", "ROAS"] == 5.0
    assert out.loc["LinkedIn", "CPA"] == 100.0
    assert out.loc["Meta", "Spend"] == 400


def test_formatters():
    assert metrics.money(1234.5) == "$1,234.50"
    assert metrics.money(float("nan")) == "-"
    assert metrics.multiple(2.8333) == "2.83x"
    assert metrics.multiple(float("nan")) == "-"
    assert metrics.pct(0.04) == "4.00%"
    assert metrics.pct(float("nan")) == "-"
