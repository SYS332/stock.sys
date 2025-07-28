"""
FastAPI Backend for Stock Analysis Application
Main application entry point with API routes and configuration
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import logging
import asyncio
from typing import Optional, List, Dict, Any
import os
from datetime import datetime, timedelta

# Import our modules
from api.routes import stocks, predictions, settings, telegram
from database.models import init_db
from services.scheduler import start_scheduler, stop_scheduler
from services.encryption import EncryptionService
from config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Stock Analysis Application...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start background scheduler
    start_scheduler()
    logger.info("Background scheduler started")
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    stop_scheduler()
    logger.info("Background scheduler stopped")

# Create FastAPI app
app = FastAPI(
    title="Stock Analysis API",
    description="Backend API for Stock Analysis Application with AI predictions and Telegram notifications",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# API status endpoint
@app.get("/api/status")
async def api_status():
    """Get API status and configuration"""
    settings = get_settings()
    
    return {
        "database": {
            "status": "connected",
            "path": settings.database_url
        },
        "services": {
            "stock_api": "configured" if settings.stock_api_key else "not_configured",
            "ai_api": "configured" if settings.ai_api_key else "not_configured",
            "telegram": "configured" if settings.telegram_bot_token else "not_configured"
        },
        "scheduler": {
            "status": "running",
            "next_run": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
    }

# Include API routes
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return {
        "error": True,
        "status_code": exc.status_code,
        "message": exc.detail,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled Exception: {str(exc)}")
    return {
        "error": True,
        "status_code": 500,
        "message": "Internal server error",
        "timestamp": datetime.utcnow().isoformat()
    }

# WebSocket endpoint for real-time updates
@app.websocket("/api/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time stock updates"""
    await websocket.accept()
    try:
        while True:
            # In a real implementation, this would send real-time stock data
            # For now, we'll send a heartbeat every 30 seconds
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(30)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )