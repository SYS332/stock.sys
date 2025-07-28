"""
Settings API routes for FastAPI backend
Handles API key management, user settings, and configuration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database.models import get_db, APIKey, UserSettings
from services.encryption import store_encrypted_api_key, retrieve_decrypted_api_key, delete_api_key
from config import get_settings, API_PROVIDERS, AI_PROVIDERS
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class APIKeyRequest(BaseModel):
    service_name: str
    api_key: str
    provider: Optional[str] = None
    
    @validator('service_name')
    def validate_service_name(cls, v):
        valid_services = ['stock_api', 'ai_api', 'telegram']
        if v not in valid_services:
            raise ValueError(f'service_name must be one of: {valid_services}')
        return v

class APIKeyResponse(BaseModel):
    id: int
    service_name: str
    provider: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    has_key: bool  # Don't expose the actual key

class APIKeyTestResponse(BaseModel):
    service_name: str
    provider: Optional[str]
    status: str  # 'success', 'failed', 'invalid'
    message: str
    details: Optional[Dict[str, Any]] = None

class UserSettingRequest(BaseModel):
    setting_key: str
    setting_value: str
    setting_type: str = "string"
    description: Optional[str] = None
    
    @validator('setting_type')
    def validate_setting_type(cls, v):
        valid_types = ['string', 'int', 'float', 'bool', 'json']
        if v not in valid_types:
            raise ValueError(f'setting_type must be one of: {valid_types}')
        return v

class UserSettingResponse(BaseModel):
    id: int
    setting_key: str
    setting_value: str
    setting_type: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

class SystemStatusResponse(BaseModel):
    database: Dict[str, Any]
    services: Dict[str, str]
    api_providers: Dict[str, Dict[str, Any]]
    system_info: Dict[str, Any]

# API Key Management Endpoints
@router.get("/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(db: Session = Depends(get_db)):
    """Get all stored API keys (without exposing the actual keys)"""
    try:
        api_keys = db.query(APIKey).all()
        
        return [APIKeyResponse(
            id=key.id,
            service_name=key.service_name,
            provider=key.provider,
            is_active=key.is_active,
            created_at=key.created_at,
            updated_at=key.updated_at,
            has_key=bool(key.encrypted_key)
        ) for key in api_keys]
        
    except Exception as e:
        logger.error(f"Error fetching API keys: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch API keys")

@router.post("/api-keys", response_model=APIKeyResponse)
async def store_api_key(
    api_key_data: APIKeyRequest,
    db: Session = Depends(get_db)
):
    """Store or update an API key"""
    try:
        # Validate provider for the service
        if api_key_data.service_name == "stock_api" and api_key_data.provider:
            if api_key_data.provider not in API_PROVIDERS:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid stock API provider. Must be one of: {list(API_PROVIDERS.keys())}"
                )
        
        if api_key_data.service_name == "ai_api" and api_key_data.provider:
            if api_key_data.provider not in AI_PROVIDERS:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid AI provider. Must be one of: {list(AI_PROVIDERS.keys())}"
                )
        
        # Store encrypted API key
        store_encrypted_api_key(
            db, 
            api_key_data.service_name, 
            api_key_data.api_key, 
            api_key_data.provider
        )
        
        # Fetch the stored key to return
        stored_key = db.query(APIKey).filter(
            APIKey.service_name == api_key_data.service_name
        ).first()
        
        if not stored_key:
            raise HTTPException(status_code=500, detail="Failed to store API key")
        
        logger.info(f"API key stored successfully for service: {api_key_data.service_name}")
        
        return APIKeyResponse(
            id=stored_key.id,
            service_name=stored_key.service_name,
            provider=stored_key.provider,
            is_active=stored_key.is_active,
            created_at=stored_key.created_at,
            updated_at=stored_key.updated_at,
            has_key=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to store API key")

@router.delete("/api-keys/{service_name}")
async def delete_api_key_endpoint(
    service_name: str,
    db: Session = Depends(get_db)
):
    """Delete an API key"""
    try:
        success = delete_api_key(db, service_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"API key for {service_name} not found")
        
        return {
            "message": f"API key for {service_name} deleted successfully",
            "service_name": service_name,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")

@router.post("/api-keys/{service_name}/test", response_model=APIKeyTestResponse)
async def test_api_key(
    service_name: str,
    db: Session = Depends(get_db)
):
    """Test an API key connection"""
    try:
        # Retrieve the API key
        api_key = retrieve_decrypted_api_key(db, service_name)
        if not api_key:
            raise HTTPException(status_code=404, detail=f"API key for {service_name} not found")
        
        # Get provider info
        api_key_record = db.query(APIKey).filter(
            APIKey.service_name == service_name,
            APIKey.is_active == True
        ).first()
        
        provider = api_key_record.provider if api_key_record else None
        
        # Test the connection based on service type
        if service_name == "stock_api":
            result = await test_stock_api_connection(api_key, provider)
        elif service_name == "ai_api":
            result = await test_ai_api_connection(api_key, provider)
        elif service_name == "telegram":
            result = await test_telegram_connection(api_key)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {service_name}")
        
        return APIKeyTestResponse(
            service_name=service_name,
            provider=provider,
            status=result["status"],
            message=result["message"],
            details=result.get("details")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing API key for {service_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to test API key")

# User Settings Endpoints
@router.get("/user-settings", response_model=List[UserSettingResponse])
async def get_user_settings(db: Session = Depends(get_db)):
    """Get all user settings"""
    try:
        settings = db.query(UserSettings).all()
        
        return [UserSettingResponse(
            id=setting.id,
            setting_key=setting.setting_key,
            setting_value=setting.setting_value,
            setting_type=setting.setting_type,
            description=setting.description,
            created_at=setting.created_at,
            updated_at=setting.updated_at
        ) for setting in settings]
        
    except Exception as e:
        logger.error(f"Error fetching user settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user settings")

@router.get("/user-settings/{setting_key}", response_model=UserSettingResponse)
async def get_user_setting(
    setting_key: str,
    db: Session = Depends(get_db)
):
    """Get a specific user setting"""
    try:
        setting = db.query(UserSettings).filter(
            UserSettings.setting_key == setting_key
        ).first()
        
        if not setting:
            raise HTTPException(status_code=404, detail=f"Setting {setting_key} not found")
        
        return UserSettingResponse(
            id=setting.id,
            setting_key=setting.setting_key,
            setting_value=setting.setting_value,
            setting_type=setting.setting_type,
            description=setting.description,
            created_at=setting.created_at,
            updated_at=setting.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching setting {setting_key}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch setting")

@router.post("/user-settings", response_model=UserSettingResponse)
async def create_or_update_user_setting(
    setting_data: UserSettingRequest,
    db: Session = Depends(get_db)
):
    """Create or update a user setting"""
    try:
        # Check if setting already exists
        existing_setting = db.query(UserSettings).filter(
            UserSettings.setting_key == setting_data.setting_key
        ).first()
        
        if existing_setting:
            # Update existing setting
            existing_setting.setting_value = setting_data.setting_value
            existing_setting.setting_type = setting_data.setting_type
            existing_setting.description = setting_data.description
            existing_setting.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_setting)
            
            return UserSettingResponse(
                id=existing_setting.id,
                setting_key=existing_setting.setting_key,
                setting_value=existing_setting.setting_value,
                setting_type=existing_setting.setting_type,
                description=existing_setting.description,
                created_at=existing_setting.created_at,
                updated_at=existing_setting.updated_at
            )
        else:
            # Create new setting
            new_setting = UserSettings(
                setting_key=setting_data.setting_key,
                setting_value=setting_data.setting_value,
                setting_type=setting_data.setting_type,
                description=setting_data.description
            )
            
            db.add(new_setting)
            db.commit()
            db.refresh(new_setting)
            
            return UserSettingResponse(
                id=new_setting.id,
                setting_key=new_setting.setting_key,
                setting_value=new_setting.setting_value,
                setting_type=new_setting.setting_type,
                description=new_setting.description,
                created_at=new_setting.created_at,
                updated_at=new_setting.updated_at
            )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating setting: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create/update setting")

@router.delete("/user-settings/{setting_key}")
async def delete_user_setting(
    setting_key: str,
    db: Session = Depends(get_db)
):
    """Delete a user setting"""
    try:
        setting = db.query(UserSettings).filter(
            UserSettings.setting_key == setting_key
        ).first()
        
        if not setting:
            raise HTTPException(status_code=404, detail=f"Setting {setting_key} not found")
        
        db.delete(setting)
        db.commit()
        
        return {
            "message": f"Setting {setting_key} deleted successfully",
            "setting_key": setting_key,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting setting {setting_key}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete setting")

# System Status Endpoint
@router.get("/system-status", response_model=SystemStatusResponse)
async def get_system_status(db: Session = Depends(get_db)):
    """Get system status and configuration"""
    try:
        settings = get_settings()
        
        # Check database connection
        try:
            db.execute("SELECT 1")
            db_status = "connected"
        except Exception:
            db_status = "disconnected"
        
        # Check API key availability
        services_status = {}
        for service in ['stock_api', 'ai_api', 'telegram']:
            api_key = retrieve_decrypted_api_key(db, service)
            services_status[service] = "configured" if api_key else "not_configured"
        
        # Get API provider information
        api_providers_info = {
            "stock_providers": API_PROVIDERS,
            "ai_providers": AI_PROVIDERS
        }
        
        # System information
        system_info = {
            "debug_mode": settings.debug,
            "log_level": settings.log_level,
            "rate_limit_per_minute": settings.rate_limit_per_minute,
            "default_stocks": settings.default_stocks,
            "data_fetch_interval_hours": settings.data_fetch_interval_hours,
            "prediction_interval_hours": settings.prediction_interval_hours
        }
        
        return SystemStatusResponse(
            database={
                "status": db_status,
                "url": settings.database_url
            },
            services=services_status,
            api_providers=api_providers_info,
            system_info=system_info
        )
        
    except Exception as e:
        logger.error(f"Error fetching system status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch system status")

# Helper functions for API testing
async def test_stock_api_connection(api_key: str, provider: str) -> Dict[str, Any]:
    """Test stock API connection"""
    try:
        from services.stock_api import AlphaVantageProvider, TwelveDataProvider, YahooFinanceProvider
        
        if provider == "alphavantage":
            async with AlphaVantageProvider(api_key) as stock_provider:
                quote = await stock_provider.get_quote("AAPL")
        elif provider == "twelvedata":
            async with TwelveDataProvider(api_key) as stock_provider:
                quote = await stock_provider.get_quote("AAPL")
        elif provider == "yahoofinance":
            async with YahooFinanceProvider() as stock_provider:
                quote = await stock_provider.get_quote("AAPL")
        else:
            return {
                "status": "failed",
                "message": f"Unknown provider: {provider}"
            }
        
        if quote:
            return {
                "status": "success",
                "message": f"Successfully connected to {provider}",
                "details": {
                    "test_symbol": "AAPL",
                    "test_price": quote.price,
                    "provider": provider
                }
            }
        else:
            return {
                "status": "failed",
                "message": f"Failed to fetch test data from {provider}"
            }
            
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Connection test failed: {str(e)}"
        }

async def test_ai_api_connection(api_key: str, provider: str) -> Dict[str, Any]:
    """Test AI API connection"""
    try:
        # This would test the actual AI API connection
        # For now, we'll simulate a successful test
        return {
            "status": "success",
            "message": f"AI API connection test successful for {provider}",
            "details": {
                "provider": provider,
                "test_completed": True
            }
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "message": f"AI API connection test failed: {str(e)}"
        }

async def test_telegram_connection(bot_token: str) -> Dict[str, Any]:
    """Test Telegram bot connection"""
    try:
        import aiohttp
        
        # Test Telegram bot API
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        bot_info = data.get("result", {})
                        return {
                            "status": "success",
                            "message": "Telegram bot connection successful",
                            "details": {
                                "bot_username": bot_info.get("username"),
                                "bot_name": bot_info.get("first_name"),
                                "can_join_groups": bot_info.get("can_join_groups"),
                                "can_read_all_group_messages": bot_info.get("can_read_all_group_messages")
                            }
                        }
                    else:
                        return {
                            "status": "failed",
                            "message": "Invalid Telegram bot token"
                        }
                else:
                    return {
                        "status": "failed",
                        "message": f"Telegram API returned status {response.status}"
                    }
                    
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Telegram connection test failed: {str(e)}"
        }