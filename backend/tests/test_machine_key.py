"""Machine-ingestion key checks: constant-time comparison and no shipped default in production."""
import pytest
from types import SimpleNamespace
from app.core.exceptions import AppException
from app.dependencies import integration


def settings(env, key):
    return SimpleNamespace(app_env=env, machine_integration_key=key)


def test_wrong_missing_and_correct_keys(monkeypatch):
    monkeypatch.setattr(integration, 'get_settings', lambda: settings('development', 'unit-test-key-123'))
    integration.verify_machine_integration_key('unit-test-key-123')
    for bad in (None, '', 'unit-test-key-124'):
        with pytest.raises(AppException) as error:
            integration.verify_machine_integration_key(bad)
        assert error.value.status_code == 401


def test_shipped_default_key_is_refused_in_production(monkeypatch):
    monkeypatch.setattr(integration, 'get_settings', lambda: settings('production', integration.SHIPPED_DEFAULT_KEY))
    with pytest.raises(AppException) as error:
        integration.verify_machine_integration_key(integration.SHIPPED_DEFAULT_KEY)
    assert error.value.status_code == 503
