"""
Database models for the Stock Analysis Application
SQLAlchemy models for SQLite database
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import os
from typing import Optional
from config import get_settings

Base = declarative_base()

class APIKey(Base):
    """Store encrypted API keys"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(50), unique=True, nullable=False)  # 'stock_api', 'ai_api', 'telegram'
    encrypted_key = Column(Text, nullable=False)
    provider = Column(String(50), nullable=True)  # 'alphavantage', 'openai', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Stock(Base):
    """Stock information"""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    currency = Column(String(3), default="USD")
    exchange = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    prices = relationship("StockPrice", back_populates="stock", cascade="all, delete-orphan")
    metrics = relationship("StockMetric", back_populates="stock", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="stock", cascade="all, delete-orphan")

class StockPrice(Base):
    """Daily stock price data"""
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    adjusted_close = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock = relationship("Stock", back_populates="prices")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_stock_date', 'stock_id', 'date'),
    )

class StockMetric(Base):
    """Technical indicators and metrics"""
    __tablename__ = "stock_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    
    # Technical indicators
    rsi = Column(Float, nullable=True)  # Relative Strength Index
    macd = Column(Float, nullable=True)  # MACD
    macd_signal = Column(Float, nullable=True)  # MACD Signal
    macd_histogram = Column(Float, nullable=True)  # MACD Histogram
    moving_avg_20 = Column(Float, nullable=True)  # 20-day moving average
    moving_avg_50 = Column(Float, nullable=True)  # 50-day moving average
    moving_avg_200 = Column(Float, nullable=True)  # 200-day moving average
    bollinger_upper = Column(Float, nullable=True)  # Bollinger Band Upper
    bollinger_lower = Column(Float, nullable=True)  # Bollinger Band Lower
    
    # Volume indicators
    volume_sma = Column(Float, nullable=True)  # Volume Simple Moving Average
    
    # Volatility
    volatility = Column(Float, nullable=True)  # Historical volatility
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock = relationship("Stock", back_populates="metrics")
    
    # Composite index
    __table_args__ = (
        Index('idx_stock_metric_date', 'stock_id', 'date'),
    )

class Prediction(Base):
    """AI predictions for stocks"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    prediction_date = Column(DateTime, nullable=False, index=True)
    
    # Prediction details
    timeframe = Column(String(20), nullable=False)  # 'short', 'medium', 'long'
    prediction_type = Column(String(20), nullable=False)  # 'bullish', 'bearish', 'neutral'
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    target_price = Column(Float, nullable=True)
    
    # AI model info
    ai_provider = Column(String(50), nullable=False)  # 'openai', 'claude', etc.
    model_version = Column(String(100), nullable=True)
    
    # Prediction text
    reasoning = Column(Text, nullable=True)
    signals_used = Column(Text, nullable=True)  # JSON string of signals
    
    # Accuracy tracking
    actual_price = Column(Float, nullable=True)  # Filled when timeframe expires
    accuracy_score = Column(Float, nullable=True)  # 0.0 to 1.0
    is_evaluated = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock = relationship("Stock", back_populates="predictions")
    
    # Indexes
    __table_args__ = (
        Index('idx_prediction_stock_date', 'stock_id', 'prediction_date'),
        Index('idx_prediction_timeframe', 'timeframe'),
    )

class TelegramConfig(Base):
    """Telegram bot configuration"""
    __tablename__ = "telegram_config"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String(50), nullable=False)
    bot_token_encrypted = Column(Text, nullable=False)
    
    # Notification preferences
    daily_summary = Column(Boolean, default=True)
    price_alerts = Column(Boolean, default=True)
    prediction_alerts = Column(Boolean, default=True)
    notification_time = Column(String(5), default="09:00")  # HH:MM format
    
    # Alert thresholds
    price_change_threshold = Column(Float, default=5.0)  # Percentage
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class UserSettings(Base):
    """User application settings"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=True)
    setting_type = Column(String(20), default="string")  # 'string', 'int', 'float', 'bool', 'json'
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database engine and session
engine = None
SessionLocal = None

def get_database_url():
    """Get database URL from settings"""
    settings = get_settings()
    return settings.database_url

def create_database_engine():
    """Create database engine"""
    global engine
    database_url = get_database_url()
    
    # Ensure data directory exists
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        echo=False  # Set to True for SQL debugging
    )
    
    return engine

def create_session_local():
    """Create session local"""
    global SessionLocal
    if engine is None:
        create_database_engine()
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal

def get_db():
    """Dependency to get database session"""
    if SessionLocal is None:
        create_session_local()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """Initialize database tables"""
    global engine
    
    if engine is None:
        create_database_engine()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize default data
    await init_default_data()

async def init_default_data():
    """Initialize default data"""
    if SessionLocal is None:
        create_session_local()
    
    db = SessionLocal()
    try:
        # Add default stocks if they don't exist
        settings = get_settings()
        for symbol in settings.default_stocks:
            existing_stock = db.query(Stock).filter(Stock.symbol == symbol).first()
            if not existing_stock:
                stock = Stock(
                    symbol=symbol,
                    name=f"{symbol} Inc.",  # Placeholder name
                    sector="Technology",  # Placeholder sector
                    is_active=True
                )
                db.add(stock)
        
        # Add default user settings
        default_settings = [
            ("theme", "dark", "string", "Application theme"),
            ("default_timeframe", "1D", "string", "Default chart timeframe"),
            ("auto_refresh", "true", "bool", "Auto refresh data"),
            ("refresh_interval", "60", "int", "Refresh interval in seconds"),
        ]
        
        for key, value, type_, desc in default_settings:
            existing_setting = db.query(UserSettings).filter(UserSettings.setting_key == key).first()
            if not existing_setting:
                setting = UserSettings(
                    setting_key=key,
                    setting_value=value,
                    setting_type=type_,
                    description=desc
                )
                db.add(setting)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Database utility functions
def get_stock_by_symbol(db, symbol: str) -> Optional[Stock]:
    """Get stock by symbol"""
    return db.query(Stock).filter(Stock.symbol == symbol, Stock.is_active == True).first()

def get_latest_price(db, stock_id: int) -> Optional[StockPrice]:
    """Get latest price for a stock"""
    return db.query(StockPrice).filter(
        StockPrice.stock_id == stock_id
    ).order_by(StockPrice.date.desc()).first()

def get_latest_metrics(db, stock_id: int) -> Optional[StockMetric]:
    """Get latest metrics for a stock"""
    return db.query(StockMetric).filter(
        StockMetric.stock_id == stock_id
    ).order_by(StockMetric.date.desc()).first()

def get_recent_predictions(db, stock_id: int, limit: int = 10):
    """Get recent predictions for a stock"""
    return db.query(Prediction).filter(
        Prediction.stock_id == stock_id
    ).order_by(Prediction.prediction_date.desc()).limit(limit).all()