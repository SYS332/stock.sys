"""
Configuration settings for the Stock Analysis Application
Handles environment variables and application settings
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database settings
    database_url: str = Field(
        default="sqlite:///./data/stocks.db",
        description="Database connection URL"
    )
    
    # API Keys (will be encrypted in database)
    stock_api_key: Optional[str] = Field(
        default=None,
        description="Stock data API key"
    )
    stock_api_provider: str = Field(
        default="alphavantage",
        description="Stock API provider (alphavantage, twelvedata, yahoofinance)"
    )
    
    ai_api_key: Optional[str] = Field(
        default=None,
        description="AI service API key"
    )
    ai_api_provider: str = Field(
        default="openai",
        description="AI service provider (openai, claude, custom)"
    )
    
    telegram_bot_token: Optional[str] = Field(
        default=None,
        description="Telegram bot token for notifications"
    )
    telegram_chat_id: Optional[str] = Field(
        default=None,
        description="Telegram chat ID for notifications"
    )
    
    # Security settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for encryption"
    )
    encryption_key: Optional[str] = Field(
        default=None,
        description="Encryption key for sensitive data"
    )
    
    # Application settings
    debug: bool = Field(
        default=True,
        description="Debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # API Rate limiting
    rate_limit_per_minute: int = Field(
        default=60,
        description="API rate limit per minute"
    )
    
    # Stock data settings
    default_stocks: list = Field(
        default=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        description="Default stocks to track"
    )
    
    # Scheduler settings
    data_fetch_interval_hours: int = Field(
        default=1,
        description="Hours between data fetches"
    )
    prediction_interval_hours: int = Field(
        default=6,
        description="Hours between AI predictions"
    )
    telegram_notification_hour: int = Field(
        default=9,
        description="Hour of day to send daily Telegram notifications (0-23)"
    )
    
    # External API URLs
    alphavantage_base_url: str = "https://www.alphavantage.co/query"
    twelvedata_base_url: str = "https://api.twelvedata.com"
    openai_base_url: str = "https://api.openai.com/v1"
    claude_base_url: str = "https://api.anthropic.com/v1"
    
    # WebSocket settings
    websocket_heartbeat_interval: int = Field(
        default=30,
        description="WebSocket heartbeat interval in seconds"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()

# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    database_url: str = "sqlite:///./data/stocks_dev.db"

class ProductionSettings(Settings):
    """Production environment settings"""
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/stocks_prod.db"
    secret_key: str = Field(..., description="Must be set in production")

class TestSettings(Settings):
    """Test environment settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    database_url: str = "sqlite:///./data/stocks_test.db"

def get_environment_settings():
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()

# API Provider configurations
API_PROVIDERS = {
    "alphavantage": {
        "name": "Alpha Vantage",
        "base_url": "https://www.alphavantage.co/query",
        "rate_limit": 5,  # calls per minute
        "free_tier": True,
        "endpoints": {
            "quote": "GLOBAL_QUOTE",
            "daily": "TIME_SERIES_DAILY",
            "intraday": "TIME_SERIES_INTRADAY"
        }
    },
    "twelvedata": {
        "name": "Twelve Data",
        "base_url": "https://api.twelvedata.com",
        "rate_limit": 8,  # calls per minute for free tier
        "free_tier": True,
        "endpoints": {
            "quote": "quote",
            "daily": "time_series",
            "intraday": "time_series"
        }
    },
    "yahoofinance": {
        "name": "Yahoo Finance",
        "base_url": "https://query1.finance.yahoo.com/v8/finance/chart",
        "rate_limit": 100,  # unofficial, be conservative
        "free_tier": True,
        "endpoints": {
            "quote": "chart",
            "daily": "chart",
            "intraday": "chart"
        }
    }
}

AI_PROVIDERS = {
    "openai": {
        "name": "OpenAI GPT",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "default_model": "gpt-3.5-turbo"
    },
    "claude": {
        "name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "default_model": "claude-3-haiku-20240307"
    },
    "custom": {
        "name": "Custom Model",
        "base_url": "http://localhost:8080/v1",
        "models": ["custom-model"],
        "default_model": "custom-model"
    }
}

# Database table names
DB_TABLES = {
    "api_keys": "api_keys",
    "stocks": "stocks",
    "stock_prices": "stock_prices",
    "stock_metrics": "stock_metrics",
    "predictions": "predictions",
    "telegram_config": "telegram_config",
    "user_settings": "user_settings"
}