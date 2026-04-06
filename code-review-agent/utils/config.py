from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM — Gemini (free tier via Google AI Studio)
    google_api_key: str
    model_name: str = "gemini-2.5-flash"   # free tier, 10 RPM / 250 RPD

    # GitHub
    github_token: str
    github_webhook_secret: str

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "code-review-agent"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # App
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()  # type: ignore[call-arg]
