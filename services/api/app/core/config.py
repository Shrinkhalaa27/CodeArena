from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://codearena:codearena@localhost:5432/codearena"
    redis_url: str = "redis://localhost:6379/0"
    queue_backend: str = "redis"  # redis | inline (dev only) | memory (tests)
    jwt_secret: str = Field(default="change-me-use-a-long-random-value")
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    web_origin: str = "http://localhost:3000"

    judge_backend: str = "judge0"  # judge0 | fake (fake is development/test only)
    judge0_base_url: str = "http://judge0-server:2358"
    judge0_auth_token: str = ""
    judge_poll_timeout_s: float = 30.0
    judge_max_attempts: int = 3

    llm_provider: str = "none"  # none | gemini | groq | openrouter
    llm_model: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    ai_daily_quota: int = 20
    ai_max_prompt_chars: int = 8000
    ai_timeout_s: float = 20.0

    max_source_bytes: int = 64 * 1024
    max_custom_input_bytes: int = 16 * 1024

    # Dev-only bootstrap. Never set a default admin password in production.
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    seed_demo_users: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_for_runtime(self) -> None:
        if self.is_production:
            if self.jwt_secret.startswith("change-me") or len(self.jwt_secret) < 32:
                raise RuntimeError("JWT_SECRET must be a random value of 32+ chars in production")
            if self.queue_backend in ("inline", "memory"):
                raise RuntimeError("QUEUE_BACKEND must be 'redis' in production")
            if self.judge_backend == "fake":
                raise RuntimeError("JUDGE_BACKEND=fake is not allowed in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
