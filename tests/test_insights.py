from campaign_pulse import insights


def _by_level(items):
    return {i.level: i.text for i in items}


def test_top_roas_worst_cpa_and_recommendation(sample_df):
    out = insights.generate_insights(sample_df)
    texts = _by_level(out)
    assert "Google" in texts["success"] and "5.00x" in texts["success"]
    assert "LinkedIn" in texts["warning"] and "$100.00" in texts["warning"]
    assert "shifting spend from LinkedIn to Google" in texts["info"]


def test_zero_conversion_platform_is_flagged(sample_df):
    df = sample_df.copy()
    df.loc[df["Platform"] == "Meta", "Conversions"] = 0
    out = insights.generate_insights(df)
    warnings = [i.text for i in out if i.level == "warning"]
    assert any("Meta" in w and "no conversions" in w for w in warnings)


def test_empty_selection_returns_single_info(sample_df):
    out = insights.generate_insights(sample_df.iloc[0:0])
    assert len(out) == 1 and out[0].level == "info"


def test_single_platform_asks_for_more_platforms(sample_df):
    out = insights.generate_insights(sample_df[sample_df["Platform"] == "Google"])
    assert len(out) == 1
    assert out[0].level == "info" and "Google" in out[0].text
