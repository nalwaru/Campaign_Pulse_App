from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_loads_with_fallback_data():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert len(at.metric) == 6
    labels = [m.label for m in at.metric]
    assert labels == ["Total Spend", "Total Revenue", "ROAS", "Avg CPA", "Avg CPC", "Conversions"]


def test_app_has_expected_tabs_and_filters():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert [t.label for t in at.tabs] == ["Overview", "Platform & Funnels", "Trends", "AI Insights", "Ask AI"]
    assert at.sidebar.selectbox[0].options == ["Last 7 Days", "Last 30 Days", "Custom"]
    assert len(at.sidebar.multiselect) == 2
    assert len(at.sidebar.slider) == 1


def test_app_shows_insights_for_fallback_data():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert len(at.success) >= 1


def test_selecting_no_platforms_shows_warning_not_traceback():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.multiselect[0].set_value([]).run()
    assert not at.exception
    assert len(at.warning) >= 1
