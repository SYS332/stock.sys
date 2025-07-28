"""
Stock API routes for FastAPI backend
Handles stock data retrieval, quotes, and historical data
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from database.models import get_db, Stock, StockPrice, StockMetric, get_stock_by_symbol, get_latest_price
from services.stock_api import get_stock_service, StockQuote, StockHistoricalData
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class StockResponse(BaseModel):
    id: int
    symbol: str
    name: str
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[float]
    currency: str
    exchange: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class StockQuoteResponse(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    high: float
    low: float
    open: float
    previous_close: float
    timestamp: datetime
    provider: Optional[str] = None

class StockPriceResponse(BaseModel):
    date: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int

class StockHistoricalResponse(BaseModel):
    symbol: str
    data: List[StockPriceResponse]
    period: str
    provider: Optional[str] = None

class StockSearchResult(BaseModel):
    symbol: str
    name: str
    type: Optional[str]
    exchange: Optional[str]
    currency: Optional[str]

class StockCreateRequest(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    currency: str = "USD"
    exchange: Optional[str] = None

@router.get("/", response_model=List[StockResponse])
async def get_stocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get list of stocks"""
    try:
        query = db.query(Stock)
        
        if active_only:
            query = query.filter(Stock.is_active == True)
        
        stocks = query.offset(skip).limit(limit).all()
        
        return [StockResponse(
            id=stock.id,
            symbol=stock.symbol,
            name=stock.name,
            sector=stock.sector,
            industry=stock.industry,
            market_cap=stock.market_cap,
            currency=stock.currency,
            exchange=stock.exchange,
            is_active=stock.is_active,
            created_at=stock.created_at,
            updated_at=stock.updated_at
        ) for stock in stocks]
        
    except Exception as e:
        logger.error(f"Error fetching stocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch stocks")

@router.get("/{symbol}", response_model=StockResponse)
async def get_stock(symbol: str, db: Session = Depends(get_db)):
    """Get specific stock by symbol"""
    try:
        stock = get_stock_by_symbol(db, symbol.upper())
        
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        return StockResponse(
            id=stock.id,
            symbol=stock.symbol,
            name=stock.name,
            sector=stock.sector,
            industry=stock.industry,
            market_cap=stock.market_cap,
            currency=stock.currency,
            exchange=stock.exchange,
            is_active=stock.is_active,
            created_at=stock.created_at,
            updated_at=stock.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock")

@router.post("/", response_model=StockResponse)
async def create_stock(
    stock_data: StockCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new stock"""
    try:
        # Check if stock already exists
        existing_stock = get_stock_by_symbol(db, stock_data.symbol.upper())
        if existing_stock:
            raise HTTPException(status_code=400, detail=f"Stock {stock_data.symbol} already exists")
        
        # Create new stock
        new_stock = Stock(
            symbol=stock_data.symbol.upper(),
            name=stock_data.name,
            sector=stock_data.sector,
            industry=stock_data.industry,
            market_cap=stock_data.market_cap,
            currency=stock_data.currency,
            exchange=stock_data.exchange,
            is_active=True
        )
        
        db.add(new_stock)
        db.commit()
        db.refresh(new_stock)
        
        logger.info(f"Created new stock: {new_stock.symbol}")
        
        return StockResponse(
            id=new_stock.id,
            symbol=new_stock.symbol,
            name=new_stock.name,
            sector=new_stock.sector,
            industry=new_stock.industry,
            market_cap=new_stock.market_cap,
            currency=new_stock.currency,
            exchange=new_stock.exchange,
            is_active=new_stock.is_active,
            created_at=new_stock.created_at,
            updated_at=new_stock.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating stock: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create stock")

@router.get("/{symbol}/quote", response_model=StockQuoteResponse)
async def get_stock_quote(
    symbol: str,
    live: bool = Query(False, description="Fetch live data from API"),
    db: Session = Depends(get_db)
):
    """Get current stock quote"""
    try:
        symbol = symbol.upper()
        
        if live:
            # Fetch live data from API
            stock_service = get_stock_service(db)
            quote = await stock_service.get_stock_quote(symbol)
            
            if not quote:
                raise HTTPException(status_code=404, detail=f"Unable to fetch live quote for {symbol}")
            
            return StockQuoteResponse(
                symbol=quote.symbol,
                price=quote.price,
                change=quote.change,
                change_percent=quote.change_percent,
                volume=quote.volume,
                high=quote.high,
                low=quote.low,
                open=quote.open,
                previous_close=quote.previous_close,
                timestamp=quote.timestamp,
                provider=stock_service.provider_name
            )
        else:
            # Get latest data from database
            stock = get_stock_by_symbol(db, symbol)
            if not stock:
                raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
            
            latest_price = get_latest_price(db, stock.id)
            if not latest_price:
                raise HTTPException(status_code=404, detail=f"No price data found for {symbol}")
            
            # Calculate change from previous day
            previous_price = db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.date < latest_price.date
            ).order_by(StockPrice.date.desc()).first()
            
            change = 0.0
            change_percent = 0.0
            previous_close = latest_price.close_price
            
            if previous_price:
                change = latest_price.close_price - previous_price.close_price
                change_percent = (change / previous_price.close_price) * 100
                previous_close = previous_price.close_price
            
            return StockQuoteResponse(
                symbol=stock.symbol,
                price=latest_price.close_price,
                change=change,
                change_percent=change_percent,
                volume=latest_price.volume,
                high=latest_price.high_price,
                low=latest_price.low_price,
                open=latest_price.open_price,
                previous_close=previous_close,
                timestamp=latest_price.date,
                provider="database"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock quote")

@router.get("/{symbol}/historical", response_model=StockHistoricalResponse)
async def get_stock_historical(
    symbol: str,
    period: str = Query("1mo", regex="^(1mo|3mo|6mo|1y|2y|5y)$"),
    live: bool = Query(False, description="Fetch live data from API"),
    db: Session = Depends(get_db)
):
    """Get historical stock data"""
    try:
        symbol = symbol.upper()
        
        if live:
            # Fetch live data from API
            stock_service = get_stock_service(db)
            historical_data = await stock_service.get_historical_data(symbol, period)
            
            if not historical_data:
                raise HTTPException(status_code=404, detail=f"Unable to fetch historical data for {symbol}")
            
            data = []
            for i in range(len(historical_data.dates)):
                data.append(StockPriceResponse(
                    date=historical_data.dates[i],
                    open_price=historical_data.opens[i],
                    high_price=historical_data.highs[i],
                    low_price=historical_data.lows[i],
                    close_price=historical_data.closes[i],
                    volume=historical_data.volumes[i]
                ))
            
            return StockHistoricalResponse(
                symbol=symbol,
                data=data,
                period=period,
                provider=stock_service.provider_name
            )
        else:
            # Get data from database
            stock = get_stock_by_symbol(db, symbol)
            if not stock:
                raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
            
            # Calculate date range
            end_date = datetime.now()
            days_map = {
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365,
                "2y": 730,
                "5y": 1825
            }
            start_date = end_date - timedelta(days=days_map.get(period, 30))
            
            # Query historical data
            prices = db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            ).order_by(StockPrice.date.asc()).all()
            
            if not prices:
                raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")
            
            data = [StockPriceResponse(
                date=price.date,
                open_price=price.open_price,
                high_price=price.high_price,
                low_price=price.low_price,
                close_price=price.close_price,
                volume=price.volume
            ) for price in prices]
            
            return StockHistoricalResponse(
                symbol=symbol,
                data=data,
                period=period,
                provider="database"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical data")

@router.get("/search/{query}", response_model=List[StockSearchResult])
async def search_stocks(
    query: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Search for stocks by symbol or name"""
    try:
        # First search in local database
        local_results = db.query(Stock).filter(
            (Stock.symbol.ilike(f"%{query}%")) | 
            (Stock.name.ilike(f"%{query}%"))
        ).filter(Stock.is_active == True).limit(limit).all()
        
        results = []
        
        # Add local results
        for stock in local_results:
            results.append(StockSearchResult(
                symbol=stock.symbol,
                name=stock.name,
                type="Equity",
                exchange=stock.exchange,
                currency=stock.currency
            ))
        
        # If we have fewer results than requested, search via API
        if len(results) < limit:
            try:
                stock_service = get_stock_service(db)
                api_results = await stock_service.search_stocks(query)
                
                # Add API results (avoiding duplicates)
                existing_symbols = {r.symbol for r in results}
                for api_result in api_results:
                    if api_result["symbol"] not in existing_symbols and len(results) < limit:
                        results.append(StockSearchResult(
                            symbol=api_result["symbol"],
                            name=api_result["name"],
                            type=api_result.get("type", "Equity"),
                            exchange=api_result.get("exchange", ""),
                            currency=api_result.get("currency", "USD")
                        ))
                        
            except Exception as e:
                logger.warning(f"API search failed, using local results only: {str(e)}")
        
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error searching stocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search stocks")

@router.post("/{symbol}/refresh")
async def refresh_stock_data(
    symbol: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Refresh stock data from API"""
    try:
        symbol = symbol.upper()
        
        # Verify stock exists
        stock = get_stock_by_symbol(db, symbol)
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        # Add background task to refresh data
        background_tasks.add_task(refresh_single_stock, symbol, db)
        
        return {
            "message": f"Stock data refresh initiated for {symbol}",
            "symbol": symbol,
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating refresh for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate stock refresh")

@router.post("/refresh-all")
async def refresh_all_stocks(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Refresh data for all active stocks"""
    try:
        # Get all active stocks
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        symbols = [stock.symbol for stock in stocks]
        
        if not symbols:
            raise HTTPException(status_code=404, detail="No active stocks found")
        
        # Add background task to refresh all stocks
        background_tasks.add_task(refresh_multiple_stocks, symbols, db)
        
        return {
            "message": f"Stock data refresh initiated for {len(symbols)} stocks",
            "symbols": symbols,
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating refresh for all stocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate stock refresh")

# Background task functions
async def refresh_single_stock(symbol: str, db: Session):
    """Background task to refresh single stock data"""
    try:
        stock_service = get_stock_service(db)
        result = await stock_service.update_stock_data([symbol])
        
        if result.get(symbol):
            logger.info(f"Successfully refreshed data for {symbol}")
        else:
            logger.error(f"Failed to refresh data for {symbol}")
            
    except Exception as e:
        logger.error(f"Background refresh failed for {symbol}: {str(e)}")

async def refresh_multiple_stocks(symbols: List[str], db: Session):
    """Background task to refresh multiple stocks data"""
    try:
        stock_service = get_stock_service(db)
        results = await stock_service.update_stock_data(symbols)
        
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Refreshed {successful}/{len(symbols)} stocks successfully")
        
    except Exception as e:
        logger.error(f"Background refresh failed for multiple stocks: {str(e)}")

@router.delete("/{symbol}")
async def delete_stock(symbol: str, db: Session = Depends(get_db)):
    """Soft delete a stock (mark as inactive)"""
    try:
        symbol = symbol.upper()
        stock = get_stock_by_symbol(db, symbol)
        
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        stock.is_active = False
        stock.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Soft deleted stock: {symbol}")
        
        return {
            "message": f"Stock {symbol} has been deactivated",
            "symbol": symbol,
            "status": "inactive"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting stock {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete stock")