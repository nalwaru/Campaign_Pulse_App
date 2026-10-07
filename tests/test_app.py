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


def test_semicolon_upload_shows_specific_error_not_traceback():
    raw = b"Date;Platform;Campaign;Spend;Clicks;Conversions;Revenue\n2026-01-01;Google;A;10;1;1;5\n"
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.file_uploader[0].set_value(("semi.csv", raw, "text/csv")).run()
    assert not at.exception
    assert any("semicolons" in e.value for e in at.error)


def test_ask_ai_missing_key_is_actionable(monkeypatch):
    # An explicit empty environment value overrides developer-local secrets.
    monkeypatch.setenv('OPENAI_API_KEY', '')
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any('OPENAI_API_KEY' in item.value for item in at.info)
    assert at.chat_input[0].disabled


def test_ask_ai_answers_once_and_resets_when_filters_change(monkeypatch):
    from campaign_pulse import query
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    calls = []
    def answer(question, context, history, **kwargs):
        calls.append(question)
        return 'Google has the highest ROAS.'
    monkeypatch.setattr(query, 'ask', answer)
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.chat_input[0].set_value('Which campaign is best?').run()
    assert not at.exception
    assert len(at.chat_message) == 2
    at.run()
    assert calls == ['Which campaign is best?']
    at.sidebar.multiselect[0].set_value(['Google']).run()
    assert len(at.chat_message) == 0


def test_ask_ai_error_can_be_retried(monkeypatch):
    from campaign_pulse import query
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    def fail(*args, **kwargs):
        raise query.QueryError('OpenAI quota reached.')
    monkeypatch.setattr(query, 'ask', fail)
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.chat_input[0].set_value('Why?').run()
    assert not at.exception
    assert any('quota' in item.value for item in at.error)
    assert len(at.chat_message) == 0


def test_ask_ai_resets_even_when_filters_temporarily_empty(monkeypatch):
    from campaign_pulse import query
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only')
    monkeypatch.setattr(query, 'ask', lambda *args, **kwargs: 'Answer')
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.chat_input[0].set_value('Why?').run()
    assert len(at.chat_message) == 2
    previous = at.sidebar.multiselect[0].value
    at.sidebar.multiselect[0].set_value([]).run()
    at.sidebar.multiselect[0].set_value(previous).run()
    assert len(at.chat_message) == 0
