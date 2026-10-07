import json
from types import SimpleNamespace

import httpx2 as httpx
import openai
import pytest

from campaign_pulse import query


def test_context_uses_weighted_metrics_and_filtered_rows(sample_df):
    context = json.loads(query.build_context(sample_df[sample_df.Platform == 'Google'], 'uploaded'))
    assert context['totals']['Spend'] == 200
    assert context['totals']['ROAS'] == 5
    assert context['totals']['CPA'] == 10
    assert context['source'] == 'uploaded'
    assert len(context['campaigns']['rows']) == 1
    assert context['date_range'] == ['2026-01-01', '2026-01-02']
    assert 'CTR' not in context['totals']


def test_context_bounds_rows_and_serializes_missing_ratios(sample_df):
    sample_df['Spend'] = 0
    context = json.loads(query.build_context(sample_df, 'sample', max_rows=1))
    assert context['totals']['ROAS'] is None
    assert len(context['campaigns']['rows']) == 1
    assert context['campaigns']['omitted'] == 2
    assert len(context['daily']['rows']) == 1


def test_context_ignores_unknown_columns_and_bounds_labels(sample_df):
    sample_df['private_notes'] = 'do not transmit'
    sample_df['Campaign'] = 'x' * 10000
    context = query.build_context(sample_df, 'sample')
    assert 'private_notes' not in context
    assert len(context) < 10000


def test_ask_sends_bounded_history_and_returns_answer():
    def respond(request):
        body = json.loads(request.content)
        assert body['model'] == 'gpt-4o-mini'
        assert body['store'] is False
        assert body['max_output_tokens'] == 1000
        assert len(body['input']) == 8
        assert body['input'][-1]['content'] == 'Which is best?'
        return httpx.Response(200, json={'id': 'resp_test', 'object': 'response', 'created_at': 0, 'status': 'completed', 'model': 'gpt-4o-mini', 'output': [{'type': 'message', 'id': 'msg_test', 'role': 'assistant', 'status': 'completed', 'content': [{'type': 'output_text', 'text': 'Google has the highest ROAS.', 'annotations': []}]}]})
    with openai.OpenAI(api_key='test-key', http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        history = [{'role': 'user', 'content': 'Earlier question'}] * 20
        assert query.ask('Which is best?', '{}', history, client=client) == 'Google has the highest ROAS.'


@pytest.mark.parametrize('status', [401, 429, 500])
def test_api_errors_do_not_expose_provider_details(status):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json={'error': {'message': 'sensitive-provider-detail', 'type': 'error'}}))
    with openai.OpenAI(api_key='test-key', max_retries=0, http_client=httpx.Client(transport=transport)) as client:
        with pytest.raises(query.QueryError) as error:
            query.ask('Why?', '{}', [], client=client)
        assert 'sensitive-provider-detail' not in str(error.value)


def test_empty_question_is_rejected():
    with pytest.raises(query.QueryError):
        query.ask('  ', '{}', [], client=SimpleNamespace())


def test_missing_key_and_oversized_question_rejected(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with pytest.raises(query.QueryError, match='OPENAI_API_KEY'):
        query.ask('Why?', '{}', [])
    with pytest.raises(query.QueryError, match='characters'):
        query.ask('x' * 2001, '{}', [], client=SimpleNamespace())


def test_timeout_has_actionable_safe_error():
    def timeout(request):
        raise httpx.ReadTimeout('sensitive timeout', request=request)
    with openai.OpenAI(api_key='test-key', max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(timeout))) as client:
        with pytest.raises(query.QueryError, match='timed out') as error:
            query.ask('Why?', '{}', [], client=client)
        assert 'sensitive' not in str(error.value)


def test_empty_response_is_retryable():
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output_text='')))
    with pytest.raises(query.QueryError, match='no answer'):
        query.ask('Why?', '{}', [], client=client)


def test_partial_optional_data_is_unavailable(sample_df):
    sample_df['Impressions'] = [1000, None, 1000, 1000, 1000, 1000]
    context = json.loads(query.build_context(sample_df, 'uploaded'))
    assert context['totals']['CTR'] is None
    meta = next(row for row in context['platforms']['rows'] if row['Platform'] == 'Meta')
    assert meta['CTR'] is None
    assert meta['Impressions'] is None
