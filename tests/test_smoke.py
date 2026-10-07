def test_fixture_totals(sample_df):
    assert sample_df["Spend"].sum() == 1200
    assert sample_df["Revenue"].sum() == 3400
