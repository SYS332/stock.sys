"""
Background Scheduler Service for Stock Analysis Application
Handles scheduled tasks like data fetching, predictions, and notifications
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from config import get_settings
from database.models import get_db, Stock, StockPrice, Prediction
from services.stock_api import get_stock_service
from services.ai_prediction import get_ai_prediction_service
from services.telegram_bot import send_daily_notifications, send_price_alerts, StockAlert

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

class SchedulerService:
    """Service for managing scheduled tasks"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=pytz.UTC)
        self.is_running = False
        self.settings = get_settings()
    
    def start(self):
        """Start the scheduler"""
        try:
            if not self.is_running:
                self._setup_jobs()
                self.scheduler.start()
                self.is_running = True
                logger.info("Scheduler started successfully")
            else:
                logger.warning("Scheduler is already running")
                
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise
    
    def stop(self):
        """Stop the scheduler"""
        try:
            if self.is_running:
                self.scheduler.shutdown(wait=False)
                self.is_running = False
                logger.info("Scheduler stopped successfully")
            else:
                logger.warning("Scheduler is not running")
                
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {str(e)}")
    
    def _setup_jobs(self):
        """Setup scheduled jobs"""
        try:
            # Stock data fetching job - every hour during market hours
            self.scheduler.add_job(
                fetch_stock_data_job,
                trigger=IntervalTrigger(hours=self.settings.data_fetch_interval_hours),
                id="fetch_stock_data",
                name="Fetch Stock Data",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300  # 5 minutes grace time
            )
            
            # AI predictions job - every 6 hours
            self.scheduler.add_job(
                generate_predictions_job,
                trigger=IntervalTrigger(hours=self.settings.prediction_interval_hours),
                id="generate_predictions",
                name="Generate AI Predictions",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=600  # 10 minutes grace time
            )
            
            # Daily notifications job - at specified time
            notification_hour = self.settings.telegram_notification_hour
            self.scheduler.add_job(
                daily_notifications_job,
                trigger=CronTrigger(hour=notification_hour, minute=0),
                id="daily_notifications",
                name="Send Daily Notifications",
                max_instances=1,
                coalesce=True
            )
            
            # Price alerts monitoring job - every 5 minutes during market hours
            self.scheduler.add_job(
                price_alerts_job,
                trigger=IntervalTrigger(minutes=5),
                id="price_alerts",
                name="Monitor Price Alerts",
                max_instances=1,
                coalesce=True
            )
            
            # Prediction evaluation job - daily at midnight
            self.scheduler.add_job(
                evaluate_predictions_job,
                trigger=CronTrigger(hour=0, minute=0),
                id="evaluate_predictions",
                name="Evaluate Predictions",
                max_instances=1,
                coalesce=True
            )
            
            # Database cleanup job - weekly on Sunday at 2 AM
            self.scheduler.add_job(
                database_cleanup_job,
                trigger=CronTrigger(day_of_week=6, hour=2, minute=0),  # Sunday
                id="database_cleanup",
                name="Database Cleanup",
                max_instances=1,
                coalesce=True
            )
            
            logger.info("Scheduled jobs configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup scheduled jobs: {str(e)}")
            raise
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all scheduled jobs"""
        try:
            jobs_info = []
            
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                jobs_info.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": next_run.isoformat() if next_run else None,
                    "trigger": str(job.trigger),
                    "max_instances": job.max_instances,
                    "coalesce": job.coalesce
                })
            
            return {
                "scheduler_running": self.is_running,
                "total_jobs": len(jobs_info),
                "jobs": jobs_info
            }
            
        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}")
            return {
                "scheduler_running": self.is_running,
                "total_jobs": 0,
                "jobs": [],
                "error": str(e)
            }
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a specific job"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job {job_id} paused")
            return True
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {str(e)}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a specific job"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job {job_id} resumed")
            return True
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {str(e)}")
            return False
    
    def run_job_now(self, job_id: str) -> bool:
        """Run a specific job immediately"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now(pytz.UTC))
                logger.info(f"Job {job_id} scheduled to run immediately")
                return True
            else:
                logger.error(f"Job {job_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to run job {job_id} immediately: {str(e)}")
            return False

# Scheduled job functions
async def fetch_stock_data_job():
    """Scheduled job to fetch stock data"""
    try:
        logger.info("Starting scheduled stock data fetch")
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Get all active stocks
            active_stocks = db.query(Stock).filter(Stock.is_active == True).all()
            symbols = [stock.symbol for stock in active_stocks]
            
            if not symbols:
                logger.warning("No active stocks found for data fetching")
                return
            
            # Fetch data for all stocks
            stock_service = get_stock_service(db)
            results = await stock_service.update_stock_data(symbols)
            
            successful = sum(1 for success in results.values() if success)
            logger.info(f"Stock data fetch completed: {successful}/{len(symbols)} successful")
            
            # Log any failures
            failed_symbols = [symbol for symbol, success in results.items() if not success]
            if failed_symbols:
                logger.warning(f"Failed to fetch data for: {', '.join(failed_symbols)}")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Stock data fetch job failed: {str(e)}")

async def generate_predictions_job():
    """Scheduled job to generate AI predictions"""
    try:
        logger.info("Starting scheduled AI predictions generation")
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Get stocks that need predictions (haven't had one in the last 6 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=6)
            
            # Get all active stocks
            active_stocks = db.query(Stock).filter(Stock.is_active == True).all()
            
            stocks_needing_predictions = []
            for stock in active_stocks:
                # Check if stock has recent prediction
                recent_prediction = db.query(Prediction).filter(
                    Prediction.stock_id == stock.id,
                    Prediction.prediction_date >= cutoff_time
                ).first()
                
                if not recent_prediction:
                    stocks_needing_predictions.append(stock.symbol)
            
            if not stocks_needing_predictions:
                logger.info("All stocks have recent predictions")
                return
            
            # Generate predictions
            ai_service = get_ai_prediction_service(db)
            successful = 0
            
            for symbol in stocks_needing_predictions:
                try:
                    prediction = await ai_service.generate_prediction(symbol, "medium")
                    if prediction:
                        successful += 1
                    
                    # Small delay to avoid overwhelming AI API
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to generate prediction for {symbol}: {str(e)}")
            
            logger.info(f"AI predictions generation completed: {successful}/{len(stocks_needing_predictions)} successful")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"AI predictions job failed: {str(e)}")

async def daily_notifications_job():
    """Scheduled job to send daily notifications"""
    try:
        logger.info("Starting daily notifications job")
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            await send_daily_notifications(db)
            logger.info("Daily notifications job completed")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Daily notifications job failed: {str(e)}")

async def price_alerts_job():
    """Scheduled job to monitor price alerts"""
    try:
        logger.info("Starting price alerts monitoring")
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Get stocks with significant price changes
            alerts = []
            
            # Get all active stocks
            active_stocks = db.query(Stock).filter(Stock.is_active == True).all()
            
            for stock in active_stocks:
                # Get latest two prices
                latest_prices = db.query(StockPrice).filter(
                    StockPrice.stock_id == stock.id
                ).order_by(StockPrice.date.desc()).limit(2).all()
                
                if len(latest_prices) >= 2:
                    current_price = latest_prices[0]
                    previous_price = latest_prices[1]
                    
                    # Calculate change percentage
                    change_percent = ((current_price.close_price - previous_price.close_price) / previous_price.close_price) * 100
                    
                    # Check if change exceeds threshold (default 5%)
                    threshold = 5.0  # This could be made configurable per user
                    
                    if abs(change_percent) >= threshold:
                        alert = StockAlert(
                            symbol=stock.symbol,
                            current_price=current_price.close_price,
                            change_percent=change_percent,
                            alert_type="price_change",
                            message=f"Significant price movement detected: {abs(change_percent):.2f}% {'increase' if change_percent > 0 else 'decrease'}",
                            timestamp=datetime.utcnow()
                        )
                        alerts.append(alert)
            
            if alerts:
                await send_price_alerts(db, alerts)
                logger.info(f"Price alerts sent for {len(alerts)} stocks")
            else:
                logger.info("No significant price movements detected")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Price alerts job failed: {str(e)}")

async def evaluate_predictions_job():
    """Scheduled job to evaluate predictions"""
    try:
        logger.info("Starting prediction evaluation job")
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Get predictions that need evaluation
            # Short-term: 7 days old, Medium-term: 30 days old, Long-term: 90 days old
            now = datetime.utcnow()
            
            timeframe_days = {
                'short': 7,
                'medium': 30,
                'long': 90
            }
            
            evaluated_count = 0
            
            for timeframe, days in timeframe_days.items():
                cutoff_date = now - timedelta(days=days)
                
                # Get unevaluated predictions from the cutoff period
                predictions = db.query(Prediction).filter(
                    Prediction.timeframe == timeframe,
                    Prediction.prediction_date <= cutoff_date,
                    Prediction.is_evaluated == False
                ).all()
                
                for prediction in predictions:
                    try:
                        # Get actual price at evaluation time
                        stock = db.query(Stock).filter(Stock.id == prediction.stock_id).first()
                        if not stock:
                            continue
                        
                        # Get price closest to evaluation date
                        evaluation_date = prediction.prediction_date + timedelta(days=days)
                        actual_price_record = db.query(StockPrice).filter(
                            StockPrice.stock_id == stock.id,
                            StockPrice.date <= evaluation_date
                        ).order_by(StockPrice.date.desc()).first()
                        
                        if actual_price_record:
                            # Calculate accuracy
                            from api.routes.predictions import calculate_prediction_accuracy
                            
                            accuracy_score = calculate_prediction_accuracy(
                                prediction.prediction_type,
                                prediction.target_price,
                                actual_price_record.close_price,
                                prediction.confidence
                            )
                            
                            # Update prediction
                            prediction.actual_price = actual_price_record.close_price
                            prediction.accuracy_score = accuracy_score
                            prediction.is_evaluated = True
                            prediction.updated_at = now
                            
                            evaluated_count += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to evaluate prediction {prediction.id}: {str(e)}")
            
            db.commit()
            logger.info(f"Prediction evaluation completed: {evaluated_count} predictions evaluated")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Prediction evaluation job failed: {str(e)}")

async def database_cleanup_job():
    """Scheduled job to clean up old data"""
    try:
        logger.info("Starting database cleanup job")
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Clean up old price data (keep last 2 years)
            cutoff_date = datetime.utcnow() - timedelta(days=730)
            
            old_prices = db.query(StockPrice).filter(
                StockPrice.date < cutoff_date
            ).count()
            
            if old_prices > 0:
                db.query(StockPrice).filter(
                    StockPrice.date < cutoff_date
                ).delete()
                
                logger.info(f"Cleaned up {old_prices} old price records")
            
            # Clean up old predictions (keep last 1 year)
            prediction_cutoff = datetime.utcnow() - timedelta(days=365)
            
            old_predictions = db.query(Prediction).filter(
                Prediction.prediction_date < prediction_cutoff
            ).count()
            
            if old_predictions > 0:
                db.query(Prediction).filter(
                    Prediction.prediction_date < prediction_cutoff
                ).delete()
                
                logger.info(f"Cleaned up {old_predictions} old prediction records")
            
            db.commit()
            logger.info("Database cleanup completed")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Database cleanup job failed: {str(e)}")

# Global scheduler management functions
def start_scheduler():
    """Start the global scheduler"""
    global scheduler
    
    try:
        if scheduler is None:
            scheduler = SchedulerService()
        
        scheduler.start()
        
    except Exception as e:
        logger.error(f"Failed to start global scheduler: {str(e)}")
        raise

def stop_scheduler():
    """Stop the global scheduler"""
    global scheduler
    
    try:
        if scheduler and scheduler.is_running:
            scheduler.stop()
            
    except Exception as e:
        logger.error(f"Failed to stop global scheduler: {str(e)}")

def get_scheduler() -> Optional[SchedulerService]:
    """Get the global scheduler instance"""
    return scheduler

def is_market_hours() -> bool:
    """Check if it's currently market hours (9:30 AM - 4:00 PM ET, Mon-Fri)"""
    try:
        # Get current time in Eastern timezone
        et_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(et_tz)
        
        # Check if it's a weekday (0 = Monday, 6 = Sunday)
        if now_et.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if it's within market hours (9:30 AM - 4:00 PM)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now_et <= market_close
        
    except Exception as e:
        logger.error(f"Error checking market hours: {str(e)}")
        return True  # Default to True if we can't determine