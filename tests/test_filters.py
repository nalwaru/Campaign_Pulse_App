import pandas as pd

from campaign_pulse import filters

T = pd.Timestamp


def test_preset_last_7_days_anchors_to_max_date():
    assert filters.preset_range("Last 7 Days", T("2026-01-01"), T("2026-01-30")) == (T("2026-01-24"), T("2026-01-30"))


def test_preset_last_30_days_clamps_to_min_date():
    assert filters.preset_range("Last 30 Days", T("2026-01-10"), T("2026-01-30")) == (T("2026-01-10"), T("2026-01-30"))


def test_preset_custom_returns_full_range():
    assert filters.preset_range("Custom", T("2026-01-01"), T("2026-01-30")) == (T("2026-01-01"), T("2026-01-30"))


def test_normalize_range_handles_partial_selection():
    import datetime as dt

    d = dt.date(2026, 1, 5)
    assert filters.normalize_range((d,)) == (T("2026-01-05"), T("2026-01-05"))
    assert filters.normalize_range(d) == (T("2026-01-05"), T("2026-01-05"))
    assert filters.normalize_range([d, dt.date(2026, 1, 9)]) == (T("2026-01-05"), T("2026-01-09"))


def test_campaigns_for_depends_on_platforms(sample_df):
    assert filters.campaigns_for(sample_df, ["Google", "Meta"]) == ["Retargeting_V1", "Search_Brand"]


def test_apply_filters_date_range_is_inclusive(sample_df):
    out = filters.apply_filters(
        sample_df, T("2026-01-02"), T("2026-01-02"),
        ["Google", "Meta", "LinkedIn"], ["Search_Brand", "Retargeting_V1", "B2B_Outreach"], 0,
    )
    assert len(out) == 3


def test_apply_filters_platform_campaign_and_min_spend(sample_df):
    all_p = ["Google", "Meta", "LinkedIn"]
    all_c = ["Search_Brand", "Retargeting_V1", "B2B_Outreach"]
    start, end = T("2026-01-01"), T("2026-01-02")
    assert set(filters.apply_filters(sample_df, start, end, ["Meta"], all_c, 0)["Platform"]) == {"Meta"}
    assert set(filters.apply_filters(sample_df, start, end, all_p, ["Search_Brand"], 0)["Campaign"]) == {"Search_Brand"}
    assert filters.apply_filters(sample_df, start, end, all_p, all_c, 200)["Spend"].min() == 200


def test_apply_filters_can_return_empty(sample_df):
    out = filters.apply_filters(sample_df, T("2026-01-01"), T("2026-01-02"), [], [], 0)
    assert out.empty
