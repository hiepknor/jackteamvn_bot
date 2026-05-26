import pytest
from pydantic import ValidationError

from config import Settings


def make_settings(**overrides):
    values = {
        "TELEGRAM_BOT_TOKEN": "test-token",
        "TELEGRAM_ALLOWED_USER_IDS": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_empty_allowed_user_ids_allows_everyone():
    settings = make_settings()

    assert settings.allowed_user_id_list == []
    assert settings.is_user_allowed(123)
    assert settings.is_user_allowed(456)


def test_allowed_user_ids_limit_access_and_deduplicate():
    settings = make_settings(TELEGRAM_ALLOWED_USER_IDS="123, 456;123")

    assert settings.allowed_user_id_list == [123, 456]
    assert settings.is_user_allowed(123)
    assert settings.is_user_allowed(456)
    assert not settings.is_user_allowed(789)


def test_allowed_user_ids_reject_invalid_tokens():
    with pytest.raises(ValidationError, match="TELEGRAM_ALLOWED_USER_IDS"):
        make_settings(TELEGRAM_ALLOWED_USER_IDS="123,abc")
