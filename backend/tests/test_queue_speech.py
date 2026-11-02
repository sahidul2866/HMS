from types import SimpleNamespace
from urllib.error import HTTPError
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.modules.queue import speech
from app.schemas.queue import QueueSpeechRequest


@pytest.fixture(autouse=True)
def provider(monkeypatch):
    settings = SimpleNamespace(azure_speech_key='test-key', azure_speech_region='eastus')
    monkeypatch.setattr(speech, 'get_settings', lambda: settings)
    speech._cache.clear()
    speech._requests.clear()
    return settings


def response(audio=b'ID3-test-audio'):
    result = Mock()
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    result.read.return_value = audio
    return result


def test_neural_requires_credentials_and_exposes_no_key(provider):
    provider.azure_speech_key = None
    assert speech.configuration()['available'] is False
    assert 'test-key' not in str(speech.configuration())
    with pytest.raises(AppException) as error:
        speech.synthesize('Sound check', 'en-US', 'operator')
    assert error.value.code == 'neural_voice_not_configured'


@pytest.mark.parametrize('language,voice', [('en-US', 'en-US-JennyNeural'), ('bn-BD', 'bn-BD-NabanitaNeural')])
def test_uses_neural_voice_and_escapes_ssml(monkeypatch, language, voice):
    send = Mock(return_value=response())
    monkeypatch.setattr(speech, 'urlopen', send)
    assert speech.synthesize('সিরিয়াল 1 <break/> & room 2', language, 'operator') == b'ID3-test-audio'
    request = send.call_args.args[0]
    assert voice in request.data.decode('utf-8')
    assert '&lt;break/&gt; &amp;' in request.data.decode('utf-8')
    assert request.full_url == 'https://eastus.tts.speech.microsoft.com/cognitiveservices/v1'
    assert send.call_args.kwargs['timeout'] == 8


def test_repeat_announcement_reuses_bounded_audio_cache(monkeypatch):
    send = Mock(return_value=response())
    monkeypatch.setattr(speech, 'urlopen', send)
    speech.synthesize('Serial one', 'en-US', 'operator')
    speech.synthesize('Serial one', 'en-US', 'operator')
    assert send.call_count == 1


def test_provider_failure_has_a_safe_fallback_error(monkeypatch):
    monkeypatch.setattr(speech, 'urlopen', Mock(side_effect=HTTPError('https://example.test', 401, 'secret-provider-error', {}, None)))
    with pytest.raises(AppException) as error:
        speech.synthesize('Serial one', 'en-US', 'operator')
    assert error.value.code == 'neural_voice_unavailable'
    assert 'test-key' not in error.value.message
    assert 'secret-provider-error' not in error.value.message


def test_audio_request_is_limited_and_rejects_invalid_locale():
    with pytest.raises(ValidationError):
        QueueSpeechRequest(text='test', language='unsupported')
    with pytest.raises(ValidationError):
        QueueSpeechRequest(text='x' * 501)
    with pytest.raises(ValidationError):
        QueueSpeechRequest(text='invalid\x00text')


def test_rate_limit_stops_excessive_synthesis(monkeypatch):
    monkeypatch.setattr(speech, 'urlopen', Mock(return_value=response()))
    for _ in range(60):
        speech.synthesize('Serial one', 'en-US', 'operator')
    with pytest.raises(AppException) as error:
        speech.synthesize('Serial one', 'en-US', 'operator')
    assert error.value.status_code == 429
