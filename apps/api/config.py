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

    # Tavily web search
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com"

    # Python sandbox provider: subprocess | docker | e2b
    python_sandbox: str = "subprocess"
    e2b_api_key: str = ""

    # Secret encryption key — 64 hex chars (32 bytes) for AES-256-GCM
    # Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
    # If empty, secrets are stored as plaintext (dev/MVP only).
    secret_encryption_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
