import pytest

from app.core.config import Settings, get_settings


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("release", False),
        ("production", False),
        ("false", False),
        ("debug", True),
        ("development", True),
        ("true", True),
    ],
)
def test_settings_parse_common_debug_strings(raw_value, expected):
    settings = Settings(debug=raw_value)
    assert settings.debug is expected


def test_get_settings_accepts_release_env(monkeypatch):
    monkeypatch.setenv("DEBUG", "release")
    get_settings.cache_clear()

    try:
        assert get_settings().debug is False
    finally:
        get_settings.cache_clear()
