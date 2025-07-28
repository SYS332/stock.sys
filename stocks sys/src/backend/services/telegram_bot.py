"""
Telegram Bot Service for Stock Analysis Application
Handles notifications, daily summaries, and user interactions
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
from dataclasses import dataclass

from config import get_settings
from services.encryption import retrieve_decrypted_api_key
from database.models import TelegramConfig, Stock, StockPrice, Prediction

logger = logging.getLogger(__name__)

@dataclass
class TelegramMessage:
    """Telegram message data structure"""
    chat_id: str
    text: str
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = True

@dataclass
class StockAlert:
    """Stock alert data structure"""
    symbol: str
    current_price: float
    change_percent: float
    alert_type: str  # 'price_change', 'prediction', 'daily_summary'
    message: str
    timestamp: datetime

class TelegramBotService:
    """Service for Telegram bot operations"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.bot_token: Optional[str] = None
        self.base_url = "https://api.telegram.org/bot"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.initialize_bot()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def initialize_bot(self) -> bool:
        """Initialize Telegram bot with stored token"""
        try:
            # Get bot token from database
            self.bot_token = retrieve_decrypted_api_key(self.db, "telegram")
            
            if not self.bot_token:
                logger.warning("No Telegram bot token found in database")
                return False
            
            # Test bot connection
            bot_info = await self.get_bot_info()
            if bot_info:
                logger.info(f"Telegram bot initialized: @{bot_info.get('username', 'unknown')}")
                return True
            else:
                logger.error("Failed to initialize Telegram bot")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing Telegram bot: {str(e)}")
            return False
    
    async def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """Get bot information"""
        try:
            if not self.bot_token:
                return None
            
            url = f"{self.base_url}{self.bot_token}/getMe"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        return data.get("result")
                    else:
                        logger.error(f"Telegram API error: {data.get('description')}")
                        return None
                else:
                    logger.error(f"Telegram API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting bot info: {str(e)}")
            return None
    
    async def send_message(self, message: TelegramMessage) -> bool:
        """Send message to Telegram chat"""
        try:
            if not self.bot_token:
                logger.error("No bot token available")
                return False
            
            url = f"{self.base_url}{self.bot_token}/sendMessage"
            
            payload = {
                "chat_id": message.chat_id,
                "text": message.text,
                "parse_mode": message.parse_mode,
                "disable_web_page_preview": message.disable_web_page_preview
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        logger.info(f"Message sent to chat {message.chat_id}")
                        return True
                    else:
                        logger.error(f"Telegram send message error: {data.get('description')}")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"Telegram API request failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending Telegram message: {str(e)}")
            return False
    
    async def send_stock_alert(self, alert: StockAlert, chat_ids: List[str]) -> Dict[str, bool]:
        """Send stock alert to multiple chats"""
        results = {}
        
        # Format alert message
        message_text = self._format_stock_alert(alert)
        
        for chat_id in chat_ids:
            try:
                message = TelegramMessage(
                    chat_id=chat_id,
                    text=message_text
                )
                
                success = await self.send_message(message)
                results[chat_id] = success
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error sending alert to chat {chat_id}: {str(e)}")
                results[chat_id] = False
        
        return results
    
    async def send_daily_summary(self, chat_ids: List[str]) -> Dict[str, bool]:
        """Send daily stock summary to chats"""
        try:
            # Generate daily summary
            summary_text = await self._generate_daily_summary()
            
            if not summary_text:
                logger.warning("No daily summary generated")
                return {}
            
            results = {}
            
            for chat_id in chat_ids:
                try:
                    message = TelegramMessage(
                        chat_id=chat_id,
                        text=summary_text
                    )
                    
                    success = await self.send_message(message)
                    results[chat_id] = success
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error sending daily summary to chat {chat_id}: {str(e)}")
                    results[chat_id] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {str(e)}")
            return {}
    
    async def send_prediction_alert(self, symbol: str, prediction: Dict[str, Any], chat_ids: List[str]) -> Dict[str, bool]:
        """Send AI prediction alert to chats"""
        try:
            # Format prediction message
            message_text = self._format_prediction_alert(symbol, prediction)
            
            results = {}
            
            for chat_id in chat_ids:
                try:
                    message = TelegramMessage(
                        chat_id=chat_id,
                        text=message_text
                    )
                    
                    success = await self.send_message(message)
                    results[chat_id] = success
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error sending prediction alert to chat {chat_id}: {str(e)}")
                    results[chat_id] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error sending prediction alert: {str(e)}")
            return {}
    
    def _format_stock_alert(self, alert: StockAlert) -> str:
        """Format stock alert message"""
        try:
            emoji = "📈" if alert.change_percent > 0 else "📉" if alert.change_percent < 0 else "➡️"
            change_sign = "+" if alert.change_percent > 0 else ""
            
            message = f"""
🚨 <b>Stock Alert: {alert.symbol}</b>

{emoji} <b>Current Price:</b> ${alert.current_price:.2f}
📊 <b>Change:</b> {change_sign}{alert.change_percent:.2f}%

💬 <b>Alert:</b> {alert.message}

🕐 <i>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
            """.strip()
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting stock alert: {str(e)}")
            return f"Stock Alert: {alert.symbol} - {alert.message}"
    
    def _format_prediction_alert(self, symbol: str, prediction: Dict[str, Any]) -> str:
        """Format AI prediction alert message"""
        try:
            prediction_type = prediction.get('prediction_type', 'neutral')
            confidence = prediction.get('confidence', 0.0)
            target_price = prediction.get('target_price')
            timeframe = prediction.get('timeframe', 'medium')
            reasoning = prediction.get('reasoning', 'No reasoning provided')
            
            # Choose emoji based on prediction
            if prediction_type == 'bullish':
                emoji = "🚀"
                direction = "BULLISH"
            elif prediction_type == 'bearish':
                emoji = "🔻"
                direction = "BEARISH"
            else:
                emoji = "⚖️"
                direction = "NEUTRAL"
            
            # Format timeframe
            timeframe_map = {
                'short': '7 days',
                'medium': '30 days',
                'long': '90 days'
            }
            timeframe_text = timeframe_map.get(timeframe, timeframe)
            
            message = f"""
🤖 <b>AI Prediction: {symbol}</b>

{emoji} <b>Prediction:</b> {direction}
📊 <b>Confidence:</b> {confidence:.1%}
⏰ <b>Timeframe:</b> {timeframe_text}
"""
            
            if target_price:
                message += f"🎯 <b>Target Price:</b> ${target_price:.2f}\n"
            
            message += f"""
💭 <b>Analysis:</b>
{reasoning[:200]}{'...' if len(reasoning) > 200 else ''}

🕐 <i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
            """.strip()
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting prediction alert: {str(e)}")
            return f"AI Prediction for {symbol}: {prediction.get('prediction_type', 'unknown')}"
    
    async def _generate_daily_summary(self) -> Optional[str]:
        """Generate daily stock summary"""
        try:
            # Get active stocks
            active_stocks = self.db.query(Stock).filter(Stock.is_active == True).limit(10).all()
            
            if not active_stocks:
                return None
            
            # Get latest prices for each stock
            summary_data = []
            
            for stock in active_stocks:
                # Get latest price
                latest_price = self.db.query(StockPrice).filter(
                    StockPrice.stock_id == stock.id
                ).order_by(StockPrice.date.desc()).first()
                
                if latest_price:
                    # Get previous price for comparison
                    previous_price = self.db.query(StockPrice).filter(
                        StockPrice.stock_id == stock.id,
                        StockPrice.date < latest_price.date
                    ).order_by(StockPrice.date.desc()).first()
                    
                    change_percent = 0.0
                    if previous_price:
                        change_percent = ((latest_price.close_price - previous_price.close_price) / previous_price.close_price) * 100
                    
                    summary_data.append({
                        'symbol': stock.symbol,
                        'price': latest_price.close_price,
                        'change_percent': change_percent,
                        'volume': latest_price.volume
                    })
            
            if not summary_data:
                return None
            
            # Format summary message
            message = f"""
📊 <b>Daily Stock Summary</b>
📅 {datetime.now().strftime('%Y-%m-%d')}

"""
            
            for data in summary_data:
                emoji = "📈" if data['change_percent'] > 0 else "📉" if data['change_percent'] < 0 else "➡️"
                change_sign = "+" if data['change_percent'] > 0 else ""
                
                message += f"{emoji} <b>{data['symbol']}</b>: ${data['price']:.2f} ({change_sign}{data['change_percent']:.2f}%)\n"
            
            # Get recent predictions
            recent_predictions = self.db.query(Prediction).filter(
                Prediction.prediction_date >= datetime.utcnow() - timedelta(days=1)
            ).limit(3).all()
            
            if recent_predictions:
                message += "\n🤖 <b>Recent AI Predictions:</b>\n"
                
                for pred in recent_predictions:
                    stock = self.db.query(Stock).filter(Stock.id == pred.stock_id).first()
                    if stock:
                        pred_emoji = "🚀" if pred.prediction_type == 'bullish' else "🔻" if pred.prediction_type == 'bearish' else "⚖️"
                        message += f"{pred_emoji} {stock.symbol}: {pred.prediction_type.upper()} ({pred.confidence:.1%})\n"
            
            message += f"\n🕐 <i>Generated at {datetime.utcnow().strftime('%H:%M:%S UTC')}</i>"
            
            return message
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {str(e)}")
            return None
    
    async def get_active_chat_ids(self) -> List[str]:
        """Get list of active chat IDs for notifications"""
        try:
            telegram_configs = self.db.query(TelegramConfig).filter(
                TelegramConfig.is_active == True
            ).all()
            
            return [config.chat_id for config in telegram_configs]
            
        except Exception as e:
            logger.error(f"Error getting active chat IDs: {str(e)}")
            return []
    
    async def add_chat_id(self, chat_id: str, preferences: Dict[str, Any] = None) -> bool:
        """Add new chat ID for notifications"""
        try:
            # Check if chat ID already exists
            existing_config = self.db.query(TelegramConfig).filter(
                TelegramConfig.chat_id == chat_id
            ).first()
            
            if existing_config:
                # Update existing config
                existing_config.is_active = True
                if preferences:
                    existing_config.daily_summary = preferences.get('daily_summary', True)
                    existing_config.price_alerts = preferences.get('price_alerts', True)
                    existing_config.prediction_alerts = preferences.get('prediction_alerts', True)
                    existing_config.notification_time = preferences.get('notification_time', '09:00')
                    existing_config.price_change_threshold = preferences.get('price_change_threshold', 5.0)
                existing_config.updated_at = datetime.utcnow()
            else:
                # Create new config
                new_config = TelegramConfig(
                    chat_id=chat_id,
                    bot_token_encrypted="",  # Will be set separately
                    daily_summary=preferences.get('daily_summary', True) if preferences else True,
                    price_alerts=preferences.get('price_alerts', True) if preferences else True,
                    prediction_alerts=preferences.get('prediction_alerts', True) if preferences else True,
                    notification_time=preferences.get('notification_time', '09:00') if preferences else '09:00',
                    price_change_threshold=preferences.get('price_change_threshold', 5.0) if preferences else 5.0,
                    is_active=True
                )
                self.db.add(new_config)
            
            self.db.commit()
            logger.info(f"Added/updated chat ID: {chat_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding chat ID {chat_id}: {str(e)}")
            return False
    
    async def remove_chat_id(self, chat_id: str) -> bool:
        """Remove chat ID from notifications"""
        try:
            config = self.db.query(TelegramConfig).filter(
                TelegramConfig.chat_id == chat_id
            ).first()
            
            if config:
                config.is_active = False
                config.updated_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Removed chat ID: {chat_id}")
                return True
            else:
                logger.warning(f"Chat ID not found: {chat_id}")
                return False
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing chat ID {chat_id}: {str(e)}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Telegram bot connection"""
        try:
            if not self.bot_token:
                return {
                    "status": "failed",
                    "message": "No bot token available"
                }
            
            bot_info = await self.get_bot_info()
            
            if bot_info:
                return {
                    "status": "success",
                    "message": "Telegram bot connection successful",
                    "bot_info": {
                        "username": bot_info.get("username"),
                        "first_name": bot_info.get("first_name"),
                        "can_join_groups": bot_info.get("can_join_groups"),
                        "can_read_all_group_messages": bot_info.get("can_read_all_group_messages")
                    }
                }
            else:
                return {
                    "status": "failed",
                    "message": "Failed to get bot information"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Connection test failed: {str(e)}"
            }

# Notification scheduling functions
async def send_daily_notifications(db_session):
    """Send daily notifications to all active chats"""
    try:
        async with TelegramBotService(db_session) as telegram_service:
            chat_ids = await telegram_service.get_active_chat_ids()
            
            if not chat_ids:
                logger.info("No active chat IDs for daily notifications")
                return
            
            results = await telegram_service.send_daily_summary(chat_ids)
            
            successful = sum(1 for success in results.values() if success)
            logger.info(f"Daily notifications sent: {successful}/{len(chat_ids)} successful")
            
    except Exception as e:
        logger.error(f"Error sending daily notifications: {str(e)}")

async def send_price_alerts(db_session, alerts: List[StockAlert]):
    """Send price alerts to active chats"""
    try:
        async with TelegramBotService(db_session) as telegram_service:
            chat_ids = await telegram_service.get_active_chat_ids()
            
            if not chat_ids:
                logger.info("No active chat IDs for price alerts")
                return
            
            for alert in alerts:
                results = await telegram_service.send_stock_alert(alert, chat_ids)
                successful = sum(1 for success in results.values() if success)
                logger.info(f"Price alert for {alert.symbol} sent: {successful}/{len(chat_ids)} successful")
                
                # Small delay between alerts
                await asyncio.sleep(1)
                
    except Exception as e:
        logger.error(f"Error sending price alerts: {str(e)}")

def get_telegram_service(db_session) -> TelegramBotService:
    """Get Telegram bot service instance"""
    return TelegramBotService(db_session)