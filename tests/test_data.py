import pandas as pd
import pytest

from campaign_pulse import data


def test_normalize_columns_maps_aliases_and_ignores_case_and_padding():
    df = pd.DataFrame(
        columns=["  date ", "Channel", "Campaign Name", "Cost", "Click", "Conv.", "Sales", "Impr.", "Notes"]
    )
    out = data.normalize_columns(df)
    assert list(out.columns) == [
        "Date", "Platform", "Campaign", "Spend", "Clicks", "Conversions", "Revenue", "Impressions", "Notes",
    ]


def test_clean_raises_schema_error_listing_missing_columns():
    df = pd.DataFrame({"Date": ["2026-01-01"], "Platform": ["Google"]})
    with pytest.raises(data.SchemaError) as exc:
        data.clean(df)
    assert exc.value.missing == ["Campaign", "Spend", "Clicks", "Conversions", "Revenue"]


def test_clean_drops_invalid_rows_and_counts_them():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01", "not a date", "2026-01-03", "2026-01-04"],
            "Platform": ["Google"] * 4,
            "Campaign": ["A"] * 4,
            "Spend": [10, 10, -5, 10],
            "Clicks": [1, 1, 1, "abc"],
            "Conversions": [1, 1, 1, 1],
            "Revenue": [1, 1, 1, 1],
        }
    )
    out, dropped = data.clean(df)
    assert dropped == 3
    assert len(out) == 1


def test_clean_parses_currency_and_thousands_text():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01"],
            "Platform": [" Google "],
            "Campaign": ["A"],
            "Spend": ["$1,200.50"],
            "Clicks": ["1,200"],
            "Conversions": ["10"],
            "Revenue": ["$3,000"],
        }
    )
    out, dropped = data.clean(df)
    assert dropped == 0
    assert out.loc[0, "Spend"] == 1200.5
    assert out.loc[0, "Clicks"] == 1200
    assert out.loc[0, "Platform"] == "Google"


def test_clean_keeps_optional_columns_and_drops_unknown_ones():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01"], "Platform": ["G"], "Campaign": ["A"], "Spend": [1], "Clicks": [1],
            "Conversions": [1], "Revenue": [1], "Impressions": [100], "Notes": ["x"],
        }
    )
    out, _ = data.clean(df)
    assert "Impressions" in out.columns
    assert "Notes" not in out.columns


def test_parse_csv_handles_utf8_bom():
    raw = (
        "﻿Date,Platform,Campaign,Spend,Clicks,Conversions,Revenue\n"
        "2026-01-01,Google,Search_Brand,120.5,350,15,450\n"
    ).encode("utf-8")
    out, dropped = data.parse_csv(raw)
    assert dropped == 0
    assert out.loc[0, "Spend"] == 120.5


def test_parse_csv_empty_bytes_raises_data_error():
    with pytest.raises(data.DataError):
        data.parse_csv(b"")


def test_parse_csv_header_only_raises_data_error():
    with pytest.raises(data.DataError):
        data.parse_csv(b"Date,Platform,Campaign,Spend,Clicks,Conversions,Revenue\n")


def test_generate_fallback_shape_and_determinism():
    a = data.generate_fallback(days=30, seed=42, end="2026-01-30")
    b = data.generate_fallback(days=30, seed=42, end="2026-01-30")
    assert len(a) == 90
    assert a["Date"].min() == pd.Timestamp("2026-01-01")
    assert a["Date"].max() == pd.Timestamp("2026-01-30")
    pd.testing.assert_frame_equal(a, b)
    assert set(a["Platform"]) == {"Google", "Meta", "LinkedIn"}
    assert (a["Conversions"] <= a["Clicks"]).all()
    assert {"Impressions", "Landing Page Visits"} <= set(a.columns)


def test_generate_fallback_survives_clean():
    df = data.generate_fallback(end="2026-01-30")
    out, dropped = data.clean(df)
    assert dropped == 0
    assert len(out) == len(df)


def test_template_csv_round_trips_through_parse_csv():
    out, dropped = data.parse_csv(data.template_csv().encode("utf-8"))
    assert dropped == 0
    assert len(out) >= 1


def _frame(**over):
    base = {
        "Date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "Platform": ["Google", "Meta", "Google"],
        "Campaign": ["A", "B", "C"],
        "Spend": [10, 10, 10],
        "Clicks": [1, 1, 1],
        "Conversions": [1, 1, 1],
        "Revenue": [1, 1, 1],
    }
    base.update(over)
    return pd.DataFrame(base)


def test_blank_platform_and_campaign_cells_are_dropped_and_counted():
    df = _frame(Platform=["Google", None, "Meta", "Meta"], Campaign=["A", "B", None, "D"],
                Date=["2026-01-01"] * 4, Spend=[10] * 4, Clicks=[1] * 4, Conversions=[1] * 4, Revenue=[1] * 4)
    out, dropped = data.clean(df)
    assert dropped == 2
    assert sorted(out["Platform"].unique()) == ["Google", "Meta"]
    assert sorted(out["Campaign"].unique()) == ["A", "D"]
    assert out["Platform"].dtype == object


def test_dayfirst_file_parses_whole_column_day_first():
    df = _frame(Date=["02/01/2026", "13/01/2026", "03/02/2026"])
    out, dropped = data.clean(df)
    assert dropped == 0
    assert list(out["Date"]) == [pd.Timestamp("2026-01-02"), pd.Timestamp("2026-01-13"), pd.Timestamp("2026-02-03")]


def test_month_first_file_parses_month_first():
    df = _frame(Date=["01/02/2026", "01/13/2026", "02/03/2026"])
    out, _ = data.clean(df)
    assert list(out["Date"]) == [pd.Timestamp("2026-01-02"), pd.Timestamp("2026-01-13"), pd.Timestamp("2026-02-03")]


def test_ambiguous_slash_dates_prefer_month_first():
    df = _frame(Date=["01/02/2026", "03/04/2026", "05/06/2026"])
    out, _ = data.clean(df)
    assert out["Date"].iloc[0] == pd.Timestamp("2026-01-02")


def test_iso_dates_with_time_still_parse():
    df = _frame(Date=["2026-01-01 10:30:00", "2026-01-02", "2026-01-03T01:00:00"])
    out, dropped = data.clean(df)
    assert dropped == 0 and out["Date"].iloc[0] == pd.Timestamp("2026-01-01")


def test_mixed_utc_offsets_do_not_raise():
    df = _frame(Date=["2026-01-01T10:00:00+02:00", "2026-01-02T10:00:00-05:00", "2026-01-03T10:00:00Z"])
    out, dropped = data.clean(df)
    assert dropped == 0 and len(out) == 3 and out["Date"].dt.tz is None


def test_cells_failing_chosen_date_format_are_dropped():
    df = _frame(Date=["2026-01-01", "2026-01-02", "garbage"])
    out, dropped = data.clean(df)
    assert dropped == 1 and len(out) == 2


_HEADER = "Date,Platform,Campaign,Spend,Clicks,Conversions,Revenue\n"


def test_parse_csv_falls_back_to_cp1252():
    raw = (_HEADER + "2026-01-01,Google,Café,10,1,1,5\n").encode("cp1252")
    out, _ = data.parse_csv(raw)
    assert out["Campaign"].iloc[0] == "Café"


def test_parse_csv_semicolon_file_gets_specific_error():
    raw = "Date;Platform;Campaign;Spend;Clicks;Conversions;Revenue\n2026-01-01;Google;A;10;1;1;5\n".encode()
    with pytest.raises(data.DataError, match="semicolons") as exc:
        data.parse_csv(raw)
    assert not isinstance(exc.value, data.SchemaError)


def test_infinite_values_are_dropped():
    df = _frame(Spend=[10, float("inf"), "1e400"])
    out, dropped = data.clean(df)
    assert dropped == 2 and len(out) == 1
