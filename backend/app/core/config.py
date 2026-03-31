"""
Application configuration.

All settings are loaded from environment variables or a .env file.
Access config values anywhere via the exported `settings` instance.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    """Central settings object populated from environment / .env file."""

    # --- Auth ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # --- Vector store ---
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # --- CORS ---
    FRONTEND_URL: str = "http://localhost:3000"

    # --- Groq (cloud LLM — used when GROQ_API_KEY is set) ---
    GROQ_API_KEY: str = ""

    # --- Ollama (local LLM — fallback when GROQ_API_KEY is empty) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )


# Single shared instance — import this everywhere.
settings = Settings()
