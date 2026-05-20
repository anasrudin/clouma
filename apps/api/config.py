# apps/api/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    llm_base_url: str
    llm_model: str = "llama3.2"
    llm_api_key: str = "ollama"

    class Config:
        env_file = ".env"

settings = Settings()
