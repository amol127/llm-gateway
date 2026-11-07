from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    database_url: str = "postgresql+asyncpg://gateway:gateway@localhost:5433/gateway"

    redis_url: str = "redis://localhost:6379/0"
    rate_limit_capacity: int = 10      # max burst
    rate_limit_refill_per_sec: float = 0.2

settings = Settings()