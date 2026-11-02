"""Server-side neural PA synthesis. Provider credentials never reach the browser."""
from __future__ import annotations

from collections import OrderedDict, deque
from threading import Lock
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
import re

from app.core.config import get_settings
from app.core.exceptions import AppException

VOICES = {"en-US": "en-US-JennyNeural", "bn-BD": "bn-BD-NabanitaNeural"}
_cache: OrderedDict[tuple[str, str, str, str], tuple[float, bytes]] = OrderedDict()
_requests: dict[str, deque[float]] = {}
_lock = Lock()


def configuration() -> dict:
    settings = get_settings()
    return {"available": bool(settings.azure_speech_key and settings.azure_speech_region), "provider": "azure", "voices": VOICES}


def synthesize(text: str, language: str, actor_id: str) -> bytes:
    settings = get_settings()
    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise AppException(503, "neural_voice_not_configured", "Neural PA voice needs Azure Speech credentials on the server")
    region = settings.azure_speech_region.strip()
    if not re.fullmatch(r"[a-z0-9-]{1,40}", region):
        raise AppException(503, "neural_voice_configuration", "The Azure Speech region is invalid")
    voice = VOICES[language]
    # Credentials are part of the cache key so replacing a subscription never reuses old audio.
    cache_key = (region, settings.azure_speech_key, voice, text)
    now = monotonic()
    with _lock:
        for user_id in list(_requests):
            if not _requests[user_id] or now - _requests[user_id][-1] > 60:
                del _requests[user_id]
        recent = _requests.setdefault(actor_id, deque())
        while recent and now - recent[0] > 60:
            recent.popleft()
        if len(recent) >= 60:
            raise AppException(429, "neural_voice_rate_limit", "Too many PA voice requests. Try again shortly")
        recent.append(now)
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < 900:
            _cache.move_to_end(cache_key)
            return cached[1]
    ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}"><voice name="{voice}"><prosody rate="-10%">{escape(text)}</prosody></voice></speak>'
    request = Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode('utf-8'), method='POST',
        headers={"Ocp-Apim-Subscription-Key": settings.azure_speech_key, "Content-Type": "application/ssml+xml", "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3", "User-Agent": "HMS-PA"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            audio = response.read(1_000_001)
        if not audio or len(audio) > 1_000_000:
            raise ValueError('Invalid audio response')
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        # Do not expose upstream responses, subscription keys, or submitted text in errors.
        raise AppException(502, "neural_voice_unavailable", "Neural speech is unavailable. Device voice can be used until it recovers") from None
    with _lock:
        _cache[cache_key] = (monotonic(), audio)
        _cache.move_to_end(cache_key)
        while len(_cache) > 128:
            _cache.popitem(last=False)
    return audio
