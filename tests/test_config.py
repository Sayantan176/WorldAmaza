import pytest
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.config import settings


def test_settings_validation_and_safe_repr():
    safe_info = settings.safe_repr()
    assert "environment" in safe_info
    assert safe_info["groq_configured"] is True
    assert safe_info["gnews_configured"] is True
    assert safe_info["supabase_configured"] is True
    assert safe_info["resend_configured"] is True
    assert safe_info["groq_model"] == "openai/gpt-oss-120b"

    # Verify no secret values are exposed in safe_repr
    for key, val in safe_info.items():
        if isinstance(val, str):
            assert not val.startswith("gsk_")
            assert not val.startswith("re_")
            assert not val.startswith("eyJ")


def test_missing_settings_raises_error():
    class IsolatedConfig(BaseSettings):
        model_config = SettingsConfigDict(env_file=None)
        REQUIRED_SECRET_KEY: str

    with pytest.raises(ValidationError):
        IsolatedConfig()
