"""
Predictions API routes for FastAPI backend
Handles AI predictions, analysis, and prediction management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from database.models import get_db, Stock, Prediction, get_stock_by_symbol, get_recent_predictions
from services.ai_prediction import get_ai_prediction_service, PredictionResult
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class PredictionResponse(BaseModel):
    id: int
    symbol: str
    prediction_date: datetime
    timeframe: str
    prediction_type: str
    confidence: float
    target_price: Optional[float]
    ai_provider: str
    model_version: Optional[str]
    reasoning: Optional[str]
    signals_used: Optional[List[str]]
    actual_price: Optional[float]
    accuracy_score: Optional[float]
    is_evaluated: bool
    created_at: datetime

class PredictionRequest(BaseModel):
    symbol: str
    timeframe: str = "medium"
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['short', 'medium', 'long']
        if v not in valid_timeframes:
            raise ValueError(f'timeframe must be one of: {valid_timeframes}')
        return v

class PredictionSummaryResponse(BaseModel):
    symbol: str
    total_predictions: int
    accuracy_rate: float
    avg_confidence: float
    prediction_distribution: Dict[str, int]
    recent_predictions: List[PredictionResponse]

class BulkPredictionRequest(BaseModel):
    symbols: List[str]
    timeframe: str = "medium"
    
    @validator('symbols')
    def validate_symbols(cls, v):
        if len(v) == 0:
            raise ValueError('symbols list cannot be empty')
        if len(v) > 20:
            raise ValueError('cannot request predictions for more than 20 symbols at once')
        return v

class PredictionAnalysisResponse(BaseModel):
    symbol: str
    timeframe: str
    prediction_type: str
    confidence: float
    target_price: Optional[float]
    reasoning: str
    key_signals: List[str]
    risk_factors: List[str]
    market_context: Dict[str, Any]
    timestamp: datetime

@router.get("/", response_model=List[PredictionResponse])
async def get_predictions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    symbol: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    prediction_type: Optional[str] = Query(None),
    evaluated_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get predictions with optional filtering"""
    try:
        query = db.query(Prediction)
        
        # Apply filters
        if symbol:
            stock = get_stock_by_symbol(db, symbol.upper())
            if stock:
                query = query.filter(Prediction.stock_id == stock.id)
            else:
                return []  # Stock not found, return empty list
        
        if timeframe:
            query = query.filter(Prediction.timeframe == timeframe)
        
        if prediction_type:
            query = query.filter(Prediction.prediction_type == prediction_type)
        
        if evaluated_only:
            query = query.filter(Prediction.is_evaluated == True)
        
        # Order by most recent first
        predictions = query.order_by(Prediction.prediction_date.desc()).offset(skip).limit(limit).all()
        
        # Convert to response format
        result = []
        for pred in predictions:
            # Get stock symbol
            stock = db.query(Stock).filter(Stock.id == pred.stock_id).first()
            symbol = stock.symbol if stock else "UNKNOWN"
            
            # Parse signals_used JSON
            signals_used = []
            if pred.signals_used:
                try:
                    import json
                    signals_used = json.loads(pred.signals_used)
                except:
                    signals_used = []
            
            result.append(PredictionResponse(
                id=pred.id,
                symbol=symbol,
                prediction_date=pred.prediction_date,
                timeframe=pred.timeframe,
                prediction_type=pred.prediction_type,
                confidence=pred.confidence,
                target_price=pred.target_price,
                ai_provider=pred.ai_provider,
                model_version=pred.model_version,
                reasoning=pred.reasoning,
                signals_used=signals_used,
                actual_price=pred.actual_price,
                accuracy_score=pred.accuracy_score,
                is_evaluated=pred.is_evaluated,
                created_at=pred.created_at
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching predictions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch predictions")

@router.get("/{symbol}", response_model=List[PredictionResponse])
async def get_stock_predictions(
    symbol: str,
    limit: int = Query(10, ge=1, le=100),
    timeframe: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get predictions for a specific stock"""
    try:
        symbol = symbol.upper()
        stock = get_stock_by_symbol(db, symbol)
        
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        # Get recent predictions
        query = db.query(Prediction).filter(Prediction.stock_id == stock.id)
        
        if timeframe:
            query = query.filter(Prediction.timeframe == timeframe)
        
        predictions = query.order_by(Prediction.prediction_date.desc()).limit(limit).all()
        
        # Convert to response format
        result = []
        for pred in predictions:
            signals_used = []
            if pred.signals_used:
                try:
                    import json
                    signals_used = json.loads(pred.signals_used)
                except:
                    signals_used = []
            
            result.append(PredictionResponse(
                id=pred.id,
                symbol=symbol,
                prediction_date=pred.prediction_date,
                timeframe=pred.timeframe,
                prediction_type=pred.prediction_type,
                confidence=pred.confidence,
                target_price=pred.target_price,
                ai_provider=pred.ai_provider,
                model_version=pred.model_version,
                reasoning=pred.reasoning,
                signals_used=signals_used,
                actual_price=pred.actual_price,
                accuracy_score=pred.accuracy_score,
                is_evaluated=pred.is_evaluated,
                created_at=pred.created_at
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching predictions for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock predictions")

@router.post("/generate", response_model=PredictionAnalysisResponse)
async def generate_prediction(
    prediction_request: PredictionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate a new AI prediction for a stock"""
    try:
        symbol = prediction_request.symbol.upper()
        
        # Verify stock exists
        stock = get_stock_by_symbol(db, symbol)
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        # Check if we have a recent prediction (within last hour)
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_prediction = db.query(Prediction).filter(
            Prediction.stock_id == stock.id,
            Prediction.timeframe == prediction_request.timeframe,
            Prediction.prediction_date >= recent_cutoff
        ).first()
        
        if recent_prediction:
            # Return existing recent prediction
            signals_used = []
            if recent_prediction.signals_used:
                try:
                    import json
                    signals_used = json.loads(recent_prediction.signals_used)
                except:
                    signals_used = []
            
            return PredictionAnalysisResponse(
                symbol=symbol,
                timeframe=recent_prediction.timeframe,
                prediction_type=recent_prediction.prediction_type,
                confidence=recent_prediction.confidence,
                target_price=recent_prediction.target_price,
                reasoning=recent_prediction.reasoning or "No reasoning provided",
                key_signals=signals_used,
                risk_factors=["Market volatility", "Economic uncertainty"],  # Placeholder
                market_context={"source": "cached", "age_minutes": int((datetime.utcnow() - recent_prediction.prediction_date).total_seconds() / 60)},
                timestamp=recent_prediction.prediction_date
            )
        
        # Generate new prediction in background
        background_tasks.add_task(
            generate_prediction_background,
            symbol,
            prediction_request.timeframe,
            db
        )
        
        # Return immediate response indicating prediction is being generated
        return PredictionAnalysisResponse(
            symbol=symbol,
            timeframe=prediction_request.timeframe,
            prediction_type="pending",
            confidence=0.0,
            target_price=None,
            reasoning="Prediction is being generated. Please check back in a few moments.",
            key_signals=[],
            risk_factors=[],
            market_context={"source": "generating", "status": "in_progress"},
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating prediction for {prediction_request.symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate prediction")

@router.post("/generate-bulk")
async def generate_bulk_predictions(
    bulk_request: BulkPredictionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate predictions for multiple stocks"""
    try:
        symbols = [s.upper() for s in bulk_request.symbols]
        
        # Verify all stocks exist
        valid_symbols = []
        for symbol in symbols:
            stock = get_stock_by_symbol(db, symbol)
            if stock:
                valid_symbols.append(symbol)
            else:
                logger.warning(f"Stock {symbol} not found, skipping")
        
        if not valid_symbols:
            raise HTTPException(status_code=404, detail="No valid stocks found")
        
        # Generate predictions in background
        background_tasks.add_task(
            generate_bulk_predictions_background,
            valid_symbols,
            bulk_request.timeframe,
            db
        )
        
        return {
            "message": f"Bulk prediction generation initiated for {len(valid_symbols)} stocks",
            "symbols": valid_symbols,
            "timeframe": bulk_request.timeframe,
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating bulk predictions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate bulk predictions")

@router.get("/{symbol}/summary", response_model=PredictionSummaryResponse)
async def get_prediction_summary(
    symbol: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get prediction summary and statistics for a stock"""
    try:
        symbol = symbol.upper()
        stock = get_stock_by_symbol(db, symbol)
        
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        # Get predictions from the specified period
        start_date = datetime.utcnow() - timedelta(days=days)
        predictions = db.query(Prediction).filter(
            Prediction.stock_id == stock.id,
            Prediction.prediction_date >= start_date
        ).all()
        
        if not predictions:
            return PredictionSummaryResponse(
                symbol=symbol,
                total_predictions=0,
                accuracy_rate=0.0,
                avg_confidence=0.0,
                prediction_distribution={},
                recent_predictions=[]
            )
        
        # Calculate statistics
        total_predictions = len(predictions)
        evaluated_predictions = [p for p in predictions if p.is_evaluated and p.accuracy_score is not None]
        
        accuracy_rate = 0.0
        if evaluated_predictions:
            accuracy_rate = sum(p.accuracy_score for p in evaluated_predictions) / len(evaluated_predictions)
        
        avg_confidence = sum(p.confidence for p in predictions) / total_predictions
        
        # Prediction type distribution
        prediction_distribution = {}
        for pred in predictions:
            pred_type = pred.prediction_type
            prediction_distribution[pred_type] = prediction_distribution.get(pred_type, 0) + 1
        
        # Recent predictions (last 5)
        recent_predictions = sorted(predictions, key=lambda x: x.prediction_date, reverse=True)[:5]
        recent_predictions_response = []
        
        for pred in recent_predictions:
            signals_used = []
            if pred.signals_used:
                try:
                    import json
                    signals_used = json.loads(pred.signals_used)
                except:
                    signals_used = []
            
            recent_predictions_response.append(PredictionResponse(
                id=pred.id,
                symbol=symbol,
                prediction_date=pred.prediction_date,
                timeframe=pred.timeframe,
                prediction_type=pred.prediction_type,
                confidence=pred.confidence,
                target_price=pred.target_price,
                ai_provider=pred.ai_provider,
                model_version=pred.model_version,
                reasoning=pred.reasoning,
                signals_used=signals_used,
                actual_price=pred.actual_price,
                accuracy_score=pred.accuracy_score,
                is_evaluated=pred.is_evaluated,
                created_at=pred.created_at
            ))
        
        return PredictionSummaryResponse(
            symbol=symbol,
            total_predictions=total_predictions,
            accuracy_rate=accuracy_rate,
            avg_confidence=avg_confidence,
            prediction_distribution=prediction_distribution,
            recent_predictions=recent_predictions_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prediction summary for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch prediction summary")

@router.post("/evaluate/{prediction_id}")
async def evaluate_prediction(
    prediction_id: int,
    actual_price: float,
    db: Session = Depends(get_db)
):
    """Manually evaluate a prediction with actual price"""
    try:
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Calculate accuracy score
        accuracy_score = calculate_prediction_accuracy(
            prediction.prediction_type,
            prediction.target_price,
            actual_price,
            prediction.confidence
        )
        
        # Update prediction
        prediction.actual_price = actual_price
        prediction.accuracy_score = accuracy_score
        prediction.is_evaluated = True
        prediction.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Evaluated prediction {prediction_id}: accuracy {accuracy_score:.2f}")
        
        return {
            "message": "Prediction evaluated successfully",
            "prediction_id": prediction_id,
            "actual_price": actual_price,
            "accuracy_score": accuracy_score,
            "status": "evaluated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error evaluating prediction {prediction_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to evaluate prediction")

@router.delete("/{prediction_id}")
async def delete_prediction(
    prediction_id: int,
    db: Session = Depends(get_db)
):
    """Delete a prediction"""
    try:
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        db.delete(prediction)
        db.commit()
        
        logger.info(f"Deleted prediction {prediction_id}")
        
        return {
            "message": "Prediction deleted successfully",
            "prediction_id": prediction_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting prediction {prediction_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete prediction")

# Background task functions
async def generate_prediction_background(symbol: str, timeframe: str, db: Session):
    """Background task to generate a single prediction"""
    try:
        ai_service = get_ai_prediction_service(db)
        prediction = await ai_service.generate_prediction(symbol, timeframe)
        
        if prediction:
            logger.info(f"Background prediction generated for {symbol} ({timeframe})")
        else:
            logger.error(f"Failed to generate background prediction for {symbol}")
            
    except Exception as e:
        logger.error(f"Background prediction generation failed for {symbol}: {str(e)}")

async def generate_bulk_predictions_background(symbols: List[str], timeframe: str, db: Session):
    """Background task to generate multiple predictions"""
    try:
        ai_service = get_ai_prediction_service(db)
        successful = 0
        
        for symbol in symbols:
            try:
                prediction = await ai_service.generate_prediction(symbol, timeframe)
                if prediction:
                    successful += 1
                    # Add small delay to avoid overwhelming the AI API
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to generate prediction for {symbol}: {str(e)}")
        
        logger.info(f"Bulk prediction generation completed: {successful}/{len(symbols)} successful")
        
    except Exception as e:
        logger.error(f"Bulk prediction generation failed: {str(e)}")

def calculate_prediction_accuracy(
    prediction_type: str,
    target_price: Optional[float],
    actual_price: float,
    confidence: float
) -> float:
    """Calculate prediction accuracy score"""
    try:
        if prediction_type == "neutral":
            # For neutral predictions, accuracy is based on how close the actual price is to target
            if target_price is None:
                return 0.5  # Neutral score for neutral prediction without target
            
            price_diff_percent = abs(actual_price - target_price) / target_price * 100
            
            # Accuracy decreases as price difference increases
            if price_diff_percent <= 2:
                return 1.0
            elif price_diff_percent <= 5:
                return 0.8
            elif price_diff_percent <= 10:
                return 0.6
            else:
                return 0.3
        
        elif prediction_type in ["bullish", "bearish"]:
            # For directional predictions, check if direction was correct
            if target_price is None:
                return 0.5  # Can't evaluate without target price
            
            predicted_direction = "up" if prediction_type == "bullish" else "down"
            actual_direction = "up" if actual_price > target_price else "down"
            
            if predicted_direction == actual_direction:
                # Correct direction, now check magnitude
                price_diff_percent = abs(actual_price - target_price) / target_price * 100
                
                # Adjust accuracy based on confidence and price accuracy
                base_accuracy = 0.7  # Base score for correct direction
                magnitude_bonus = max(0, 0.3 - (price_diff_percent / 100))  # Bonus for price accuracy
                confidence_factor = confidence  # Weight by confidence
                
                return min(1.0, (base_accuracy + magnitude_bonus) * confidence_factor)
            else:
                # Wrong direction
                return max(0.1, 0.5 - confidence)  # Lower score, penalized by confidence
        
        return 0.5  # Default score
        
    except Exception as e:
        logger.error(f"Error calculating prediction accuracy: {str(e)}")
        return 0.0