import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core required integrations
    GROQ_API_KEY: str = Field(..., description="Groq API key for LLM operations")
    GNEWS_API_KEY: str = Field(..., description="GNews API key for news discovery")
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_PUBLISHABLE_KEY: str = Field(..., description="Supabase publishable anon key")
    RESEND_API_KEY: str = Field(..., description="Resend API key for email delivery")

    # Application settings
    APP_NAME: str = "WorldAmaze"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "worldamaze-production-grade-session-secret-key-2026-secure"
    DATABASE_URL: str = "sqlite:///./worldamaze.db"
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    
    # Email settings
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"
    EMAIL_ENABLED: bool = True

    # Scheduler settings
    DEFAULT_POLLING_INTERVAL_MINUTES: int = 30
    SCHEDULER_ENABLED: bool = True
    MAX_ARTICLES_PER_SEARCH: int = 10
    MAX_LLM_EVALUATIONS_PER_RUN: int = 15

    def safe_repr(self) -> dict:
        """Returns configuration status without revealing secrets."""
        return {
            "environment": self.ENVIRONMENT,
            "database": "configured" if self.DATABASE_URL else "missing",
            "database_type": "postgresql" if "postgres" in self.DATABASE_URL.lower() else "sqlite",
            "groq_configured": bool(self.GROQ_API_KEY and len(self.GROQ_API_KEY) > 5),
            "groq_model": self.GROQ_MODEL,
            "gnews_configured": bool(self.GNEWS_API_KEY and len(self.GNEWS_API_KEY) > 5),
            "supabase_configured": bool(self.SUPABASE_URL and self.SUPABASE_PUBLISHABLE_KEY),
            "resend_configured": bool(self.RESEND_API_KEY and len(self.RESEND_API_KEY) > 5),
            "resend_from_email": self.RESEND_FROM_EMAIL,
            "scheduler_enabled": self.SCHEDULER_ENABLED,
            "default_polling_interval": self.DEFAULT_POLLING_INTERVAL_MINUTES,
        }


# Global settings singleton
settings = Settings()
