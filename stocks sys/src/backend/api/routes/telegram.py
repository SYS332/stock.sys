"""
Telegram API routes for FastAPI backend
Handles Telegram bot configuration, notifications, and chat management
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database.models import get_db, TelegramConfig
from services.telegram_bot import get_telegram_service, TelegramMessage, StockAlert, send_daily_notifications, send_price_alerts
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class TelegramConfigResponse(BaseModel):
    id: int
    chat_id: str
    daily_summary: bool
    price_alerts: bool
    prediction_alerts: bool
    notification_time: str
    price_change_threshold: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

class TelegramConfigRequest(BaseModel):
    chat_id: str
    daily_summary: bool = True
    price_alerts: bool = True
    prediction_alerts: bool = True
    notification_time: str = "09:00"
    price_change_threshold: float = 5.0
    
    @validator('notification_time')
    def validate_notification_time(cls, v):
        try:
            # Validate HH:MM format
            time_parts = v.split(':')
            if len(time_parts) != 2:
                raise ValueError('Time must be in HH:MM format')
            
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError('Invalid time values')
            
            return v
        except (ValueError, IndexError):
            raise ValueError('notification_time must be in HH:MM format (24-hour)')
    
    @validator('price_change_threshold')
    def validate_threshold(cls, v):
        if v < 0 or v > 100:
            raise ValueError('price_change_threshold must be between 0 and 100')
        return v

class SendMessageRequest(BaseModel):
    chat_id: str
    message: str
    parse_mode: str = "HTML"

class BroadcastMessageRequest(BaseModel):
    message: str
    parse_mode: str = "HTML"
    active_chats_only: bool = True

class TelegramTestResponse(BaseModel):
    status: str
    message: str
    bot_info: Optional[Dict[str, Any]] = None

class NotificationStatsResponse(BaseModel):
    total_chats: int
    active_chats: int
    daily_summary_enabled: int
    price_alerts_enabled: int
    prediction_alerts_enabled: int
    last_notification_sent: Optional[datetime]

@router.get("/config", response_model=List[TelegramConfigResponse])
async def get_telegram_configs(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get Telegram configurations"""
    try:
        query = db.query(TelegramConfig)
        
        if active_only:
            query = query.filter(TelegramConfig.is_active == True)
        
        configs = query.all()
        
        return [TelegramConfigResponse(
            id=config.id,
            chat_id=config.chat_id,
            daily_summary=config.daily_summary,
            price_alerts=config.price_alerts,
            prediction_alerts=config.prediction_alerts,
            notification_time=config.notification_time,
            price_change_threshold=config.price_change_threshold,
            is_active=config.is_active,
            created_at=config.created_at,
            updated_at=config.updated_at
        ) for config in configs]
        
    except Exception as e:
        logger.error(f"Error fetching Telegram configs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch Telegram configurations")

@router.post("/config", response_model=TelegramConfigResponse)
async def create_or_update_telegram_config(
    config_data: TelegramConfigRequest,
    db: Session = Depends(get_db)
):
    """Create or update Telegram configuration"""
    try:
        telegram_service = get_telegram_service(db)
        
        # Add/update chat configuration
        preferences = {
            'daily_summary': config_data.daily_summary,
            'price_alerts': config_data.price_alerts,
            'prediction_alerts': config_data.prediction_alerts,
            'notification_time': config_data.notification_time,
            'price_change_threshold': config_data.price_change_threshold
        }
        
        success = await telegram_service.add_chat_id(config_data.chat_id, preferences)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create/update Telegram configuration")
        
        # Fetch the created/updated configuration
        config = db.query(TelegramConfig).filter(
            TelegramConfig.chat_id == config_data.chat_id
        ).first()
        
        if not config:
            raise HTTPException(status_code=500, detail="Configuration not found after creation")
        
        return TelegramConfigResponse(
            id=config.id,
            chat_id=config.chat_id,
            daily_summary=config.daily_summary,
            price_alerts=config.price_alerts,
            prediction_alerts=config.prediction_alerts,
            notification_time=config.notification_time,
            price_change_threshold=config.price_change_threshold,
            is_active=config.is_active,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating Telegram config: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create/update Telegram configuration")

@router.delete("/config/{chat_id}")
async def delete_telegram_config(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Delete (deactivate) Telegram configuration"""
    try:
        telegram_service = get_telegram_service(db)
        success = await telegram_service.remove_chat_id(chat_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Telegram configuration for chat {chat_id} not found")
        
        return {
            "message": f"Telegram configuration for chat {chat_id} deactivated",
            "chat_id": chat_id,
            "status": "deactivated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting Telegram config for {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete Telegram configuration")

@router.post("/send-message")
async def send_telegram_message(
    message_data: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """Send message to specific Telegram chat"""
    try:
        async with get_telegram_service(db) as telegram_service:
            message = TelegramMessage(
                chat_id=message_data.chat_id,
                text=message_data.message,
                parse_mode=message_data.parse_mode
            )
            
            success = await telegram_service.send_message(message)
            
            if success:
                return {
                    "message": "Message sent successfully",
                    "chat_id": message_data.chat_id,
                    "status": "sent"
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to send message")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending Telegram message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send Telegram message")

@router.post("/broadcast")
async def broadcast_message(
    broadcast_data: BroadcastMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Broadcast message to all active chats"""
    try:
        async with get_telegram_service(db) as telegram_service:
            chat_ids = await telegram_service.get_active_chat_ids()
            
            if not chat_ids:
                raise HTTPException(status_code=404, detail="No active chat IDs found")
            
            # Send broadcast in background
            background_tasks.add_task(
                send_broadcast_background,
                broadcast_data.message,
                chat_ids,
                broadcast_data.parse_mode,
                db
            )
            
            return {
                "message": f"Broadcast initiated to {len(chat_ids)} chats",
                "chat_count": len(chat_ids),
                "status": "queued"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error broadcasting message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast message")

@router.post("/send-daily-summary")
async def send_daily_summary(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send daily summary to all active chats"""
    try:
        # Send daily summary in background
        background_tasks.add_task(send_daily_notifications, db)
        
        return {
            "message": "Daily summary sending initiated",
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Error initiating daily summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate daily summary")

@router.post("/test-connection", response_model=TelegramTestResponse)
async def test_telegram_connection(db: Session = Depends(get_db)):
    """Test Telegram bot connection"""
    try:
        async with get_telegram_service(db) as telegram_service:
            result = await telegram_service.test_connection()
            
            return TelegramTestResponse(
                status=result["status"],
                message=result["message"],
                bot_info=result.get("bot_info")
            )
            
    except Exception as e:
        logger.error(f"Error testing Telegram connection: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to test Telegram connection")

@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(db: Session = Depends(get_db)):
    """Get notification statistics"""
    try:
        # Get all configurations
        all_configs = db.query(TelegramConfig).all()
        active_configs = [c for c in all_configs if c.is_active]
        
        # Count enabled features
        daily_summary_enabled = sum(1 for c in active_configs if c.daily_summary)
        price_alerts_enabled = sum(1 for c in active_configs if c.price_alerts)
        prediction_alerts_enabled = sum(1 for c in active_configs if c.prediction_alerts)
        
        # Get last notification time (approximate from most recent config update)
        last_notification = None
        if active_configs:
            last_notification = max(c.updated_at for c in active_configs)
        
        return NotificationStatsResponse(
            total_chats=len(all_configs),
            active_chats=len(active_configs),
            daily_summary_enabled=daily_summary_enabled,
            price_alerts_enabled=price_alerts_enabled,
            prediction_alerts_enabled=prediction_alerts_enabled,
            last_notification_sent=last_notification
        )
        
    except Exception as e:
        logger.error(f"Error fetching notification stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch notification statistics")

@router.post("/send-test-alert")
async def send_test_alert(
    symbol: str = "AAPL",
    db: Session = Depends(get_db)
):
    """Send test stock alert to all active chats"""
    try:
        # Create test alert
        test_alert = StockAlert(
            symbol=symbol,
            current_price=150.25,
            change_percent=2.5,
            alert_type="test",
            message=f"This is a test alert for {symbol}. Your notifications are working correctly!",
            timestamp=datetime.utcnow()
        )
        
        async with get_telegram_service(db) as telegram_service:
            chat_ids = await telegram_service.get_active_chat_ids()
            
            if not chat_ids:
                raise HTTPException(status_code=404, detail="No active chat IDs found")
            
            results = await telegram_service.send_stock_alert(test_alert, chat_ids)
            
            successful = sum(1 for success in results.values() if success)
            
            return {
                "message": f"Test alert sent to {successful}/{len(chat_ids)} chats",
                "symbol": symbol,
                "successful_sends": successful,
                "total_chats": len(chat_ids),
                "results": results
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send test alert")

@router.get("/active-chats")
async def get_active_chats(db: Session = Depends(get_db)):
    """Get list of active chat IDs"""
    try:
        async with get_telegram_service(db) as telegram_service:
            chat_ids = await telegram_service.get_active_chat_ids()
            
            return {
                "active_chats": chat_ids,
                "count": len(chat_ids)
            }
            
    except Exception as e:
        logger.error(f"Error fetching active chats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch active chats")

# Background task functions
async def send_broadcast_background(
    message: str,
    chat_ids: List[str],
    parse_mode: str,
    db: Session
):
    """Background task to send broadcast message"""
    try:
        async with get_telegram_service(db) as telegram_service:
            successful = 0
            
            for chat_id in chat_ids:
                try:
                    telegram_message = TelegramMessage(
                        chat_id=chat_id,
                        text=message,
                        parse_mode=parse_mode
                    )
                    
                    success = await telegram_service.send_message(telegram_message)
                    if success:
                        successful += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Failed to send broadcast to chat {chat_id}: {str(e)}")
            
            logger.info(f"Broadcast completed: {successful}/{len(chat_ids)} successful")
            
    except Exception as e:
        logger.error(f"Broadcast background task failed: {str(e)}")

# Webhook endpoint for Telegram bot (optional)
@router.post("/webhook")
async def telegram_webhook(
    update: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Handle Telegram webhook updates"""
    try:
        # Basic webhook handler - can be extended for bot commands
        logger.info(f"Received Telegram webhook update: {update}")
        
        # Extract message info if available
        if "message" in update:
            message = update["message"]
            chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "")
            
            # Handle basic commands
            if text.startswith("/start"):
                # Auto-register chat for notifications
                async with get_telegram_service(db) as telegram_service:
                    await telegram_service.add_chat_id(chat_id)
                
                # Send welcome message
                welcome_message = TelegramMessage(
                    chat_id=chat_id,
                    text="🚀 Welcome to Stock Analysis Bot!\n\nYou've been registered for notifications. You'll receive daily summaries and important stock alerts."
                )
                
                async with get_telegram_service(db) as telegram_service:
                    await telegram_service.send_message(welcome_message)
            
            elif text.startswith("/stop"):
                # Unregister chat
                async with get_telegram_service(db) as telegram_service:
                    await telegram_service.remove_chat_id(chat_id)
                
                # Send goodbye message
                goodbye_message = TelegramMessage(
                    chat_id=chat_id,
                    text="👋 You've been unsubscribed from notifications. Send /start to re-enable."
                )
                
                async with get_telegram_service(db) as telegram_service:
                    await telegram_service.send_message(goodbye_message)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error handling Telegram webhook: {str(e)}")
        return {"status": "error", "message": str(e)}