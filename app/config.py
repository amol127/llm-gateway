from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    database_url: str = "postgresql+asyncpg://gateway:gateway@localhost:5433/gateway"

settings = Settings()