"""
Application settings configuration with enhanced safety parameters
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import random


class Settings(BaseSettings):
    """Application settings with human-like behavior configuration"""

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

    # ============================================
    # SAFETY LIMITS (per day) - Conservative defaults
    # ============================================
    DAILY_LIMIT_LIKES: int = 50
    DAILY_LIMIT_FOLLOWS: int = 20
    DAILY_LIMIT_POSTS: int = 3
    DAILY_LIMIT_COMMENTS: int = 15
    DAILY_LIMIT_MESSAGES: int = 20
    DAILY_LIMIT_CONNECTIONS: int = 15

    # ============================================
    # HUMAN-LIKE BEHAVIOR SETTINGS
    # ============================================
    
    # Base delays (seconds) - will be randomized
    MIN_ACTION_DELAY: int = 45
    MAX_ACTION_DELAY: int = 180
    
    # Extended delays for risky actions (DMs, cold outreach)
    MIN_RISKY_DELAY: int = 120
    MAX_RISKY_DELAY: int = 360
    
    # Micro-delays to simulate reading/thinking (seconds)
    MIN_READ_DELAY: float = 2.0
    MAX_READ_DELAY: float = 8.0
    
    # Session behavior
    MIN_SESSION_ACTIONS: int = 3  # Min actions before long pause
    MAX_SESSION_ACTIONS: int = 12  # Max actions before mandatory pause
    SESSION_PAUSE_MIN: int = 300  # 5 min pause
    SESSION_PAUSE_MAX: int = 900  # 15 min pause
    
    # Activity windows (hours, 24h format) - when bot can work
    ACTIVITY_WINDOW_START: int = 8   # 8:00 AM
    ACTIVITY_WINDOW_END: int = 22    # 10:00 PM
    
    # Weekend activity reduction (multiplier)
    WEEKEND_ACTIVITY_MULTIPLIER: float = 0.5
    
    # ============================================
    # RETRY & CIRCUIT BREAKER
    # ============================================
    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: int = 5  # Base delay for exponential backoff
    RETRY_MAX_DELAY: int = 300  # Max retry delay (5 min)
    
    # Circuit breaker: stop after N consecutive failures
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_TIME: int = 1800  # 30 min cooldown
    
    # ============================================
    # PROXY & CONNECTION
    # ============================================
    REQUEST_TIMEOUT: int = 30
    PROXY_CHECK_INTERVAL: int = 300  # Check proxy health every 5 min
    
    # ============================================
    # TASK WORKER
    # ============================================
    NUM_TASK_WORKERS: int = 2  # Parallel task workers
    TASK_QUEUE_MAX_SIZE: int = 100
    
    # ============================================
    # ANTI-DETECTION
    # ============================================
    # Randomize order of actions within a batch
    RANDOMIZE_ACTION_ORDER: bool = True
    
    # Add random "noise" actions (view profile, scroll feed)
    ENABLE_NOISE_ACTIONS: bool = True
    NOISE_ACTION_PROBABILITY: float = 0.15  # 15% chance
    
    # Vary typing speed simulation
    MIN_TYPING_DELAY_PER_CHAR: float = 0.03
    MAX_TYPING_DELAY_PER_CHAR: float = 0.12

    # Server
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    STREAMLIT_PORT: int = 8501

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_random_delay(self, risky: bool = False) -> float:
        """Get randomized delay with human-like variation"""
        if risky:
            base = random.uniform(self.MIN_RISKY_DELAY, self.MAX_RISKY_DELAY)
        else:
            base = random.uniform(self.MIN_ACTION_DELAY, self.MAX_ACTION_DELAY)
        
        # Add ±20% random variation
        variation = base * random.uniform(-0.2, 0.2)
        return max(10, base + variation)
    
    def get_read_delay(self) -> float:
        """Get delay simulating reading content"""
        return random.uniform(self.MIN_READ_DELAY, self.MAX_READ_DELAY)
    
    def should_take_session_break(self, actions_count: int) -> bool:
        """Check if bot should take a longer break"""
        threshold = random.randint(self.MIN_SESSION_ACTIONS, self.MAX_SESSION_ACTIONS)
        return actions_count >= threshold
    
    def get_session_break_duration(self) -> int:
        """Get duration of session break"""
        return random.randint(self.SESSION_PAUSE_MIN, self.SESSION_PAUSE_MAX)
    
    def is_within_activity_window(self, hour: int) -> bool:
        """Check if current hour is within allowed activity window"""
        return self.ACTIVITY_WINDOW_START <= hour < self.ACTIVITY_WINDOW_END


# Global settings instance
settings = Settings()
