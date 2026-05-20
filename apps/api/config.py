# apps/api/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"

    # LLM (any OpenAI-compatible endpoint: NIM, OpenAI, Anthropic-proxy, Ollama)
    llm_provider: str = "nvidia"
    llm_base_url: str
    llm_model: str
    llm_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
