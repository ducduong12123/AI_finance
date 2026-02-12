import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Tìm đường dẫn tới .env file (ở thư mục gốc project)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    # System Config
    APP_NAME: str = "AI Finance Platform"
    ENV: str = "development"

    # AI Models (Google Gemini - Single Source of Truth)
    PRIMARY_MODEL: str = "gemini-2.0-flash"
    EMBEDDING_MODEL: str = "gemini-embedding-001"

    # API Keys
    GOOGLE_API_KEY: str = ""
    TAVILY_API_KEY: str = ""  # For web search tool

    # Supabase Config (Relational DB & Auth)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Qdrant Config (Vector DB)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"


settings = Settings()
