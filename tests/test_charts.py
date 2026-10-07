import pytest

from campaign_pulse import charts


def test_platform_spend_revenue_has_two_series_three_platforms(sample_df):
    fig = charts.platform_spend_revenue(sample_df)
    assert len(fig.data) == 2
    assert all(len(t.x) == 3 for t in fig.data)


def test_platform_cpa_values(sample_df):
    fig = charts.platform_cpa(sample_df)
    cpa = dict(zip(fig.data[0].x, fig.data[0].y))
    assert cpa["LinkedIn"] == 100.0


def test_funnel_without_landing_page_visits(sample_df):
    fig = charts.funnel_figure(sample_df)
    assert list(fig.data[0].y) == ["Clicks", "Conversions"]
    assert list(fig.data[0].x) == [800, 66]


def test_funnel_with_landing_page_visits(sample_df):
    df = sample_df.assign(**{"Landing Page Visits": [90] * 6})
    fig = charts.funnel_figure(df)
    assert list(fig.data[0].y) == ["Clicks", "Landing Page Visits", "Conversions"]


@pytest.mark.parametrize("metric", charts.METRIC_OPTIONS)
def test_trend_one_line_per_platform(sample_df, metric):
    fig = charts.trend_figure(sample_df, metric, moving_average=False)
    assert len(fig.data) == 3


def test_trend_moving_average_adds_dashed_traces(sample_df):
    fig = charts.trend_figure(sample_df, "Revenue", moving_average=True)
    assert len(fig.data) == 6
    assert sum(1 for t in fig.data if t.line.dash == "dash") == 3


def test_trend_roas_uses_daily_sums(sample_df):
    fig = charts.trend_figure(sample_df, "ROAS", moving_average=False)
    google = next(t for t in fig.data if t.name == "Google")
    assert list(google.y) == [5.0, 5.0]


def test_trend_single_day_does_not_crash(sample_df):
    one_day = sample_df[sample_df["Date"] == sample_df["Date"].min()]
    fig = charts.trend_figure(one_day, "Revenue", moving_average=True)
    assert len(fig.data) == 6
