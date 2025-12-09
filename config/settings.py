"""
Application settings configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/tenchat_booster.db"

    # AI Configuration
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""

    # AI Models
    AI_MODEL_COMMENTS: str = "openai/gpt-4o-mini"
    AI_MODEL_ARTICLES: str = "anthropic/claude-3.5-haiku"
    AI_MODEL_ANALYTICS: str = "deepseek/deepseek-chat"

    # TenChat Settings
    TENCHAT_BASE_URL: str = "https://tenchat.ru"

    # Safety Limits (per day)
    DAILY_LIMIT_LIKES: int = 50
    DAILY_LIMIT_FOLLOWS: int = 20
    DAILY_LIMIT_POSTS: int = 2

    # Delays (seconds)
    MIN_ACTION_DELAY: int = 60
    MAX_ACTION_DELAY: int = 180

    # Server
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    STREAMLIT_PORT: int = 8501

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
