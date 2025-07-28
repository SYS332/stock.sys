"""
Stock Data API Integration Service
Supports multiple providers: Alpha Vantage, Twelve Data, Yahoo Finance
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from abc import ABC, abstractmethod

from config import get_settings, API_PROVIDERS
from services.encryption import retrieve_decrypted_api_key

logger = logging.getLogger(__name__)

@dataclass
class StockQuote:
    """Stock quote data structure"""
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

@dataclass
class StockHistoricalData:
    """Historical stock data structure"""
    symbol: str
    dates: List[datetime]
    opens: List[float]
    highs: List[float]
    lows: List[float]
    closes: List[float]
    volumes: List[int]

class StockAPIProvider(ABC):
    """Abstract base class for stock API providers"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get current stock quote"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[StockHistoricalData]:
        """Get historical stock data"""
        pass
    
    @abstractmethod
    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """Search for stocks by name or symbol"""
        pass

class AlphaVantageProvider(StockAPIProvider):
    """Alpha Vantage API provider"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = API_PROVIDERS["alphavantage"]["base_url"]
        self.rate_limit = API_PROVIDERS["alphavantage"]["rate_limit"]
        self.last_request_time = 0
    
    async def _make_request(self, params: Dict[str, str]) -> Optional[Dict]:
        """Make rate-limited API request"""
        try:
            # Rate limiting
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time
            min_interval = 60 / self.rate_limit  # seconds between requests
            
            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)
            
            params["apikey"] = self.api_key
            
            async with self.session.get(self.base_url, params=params) as response:
                self.last_request_time = asyncio.get_event_loop().time()
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for API errors
                    if "Error Message" in data:
                        logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                        return None
                    
                    if "Note" in data:
                        logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                        return None
                    
                    return data
                else:
                    logger.error(f"Alpha Vantage API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Alpha Vantage API request error: {str(e)}")
            return None
    
    async def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get current stock quote from Alpha Vantage"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }
        
        data = await self._make_request(params)
        if not data or "Global Quote" not in data:
            return None
        
        try:
            quote_data = data["Global Quote"]
            
            return StockQuote(
                symbol=quote_data["01. symbol"],
                price=float(quote_data["05. price"]),
                change=float(quote_data["09. change"]),
                change_percent=float(quote_data["10. change percent"].replace("%", "")),
                volume=int(quote_data["06. volume"]),
                high=float(quote_data["03. high"]),
                low=float(quote_data["04. low"]),
                open=float(quote_data["02. open"]),
                previous_close=float(quote_data["08. previous close"]),
                timestamp=datetime.now()
            )
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Alpha Vantage quote data: {str(e)}")
            return None
    
    async def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[StockHistoricalData]:
        """Get historical data from Alpha Vantage"""
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact" if period == "1mo" else "full"
        }
        
        data = await self._make_request(params)
        if not data or "Time Series (Daily)" not in data:
            return None
        
        try:
            time_series = data["Time Series (Daily)"]
            
            dates = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            
            # Sort by date (most recent first)
            sorted_dates = sorted(time_series.keys(), reverse=True)
            
            # Limit based on period
            limit = 30 if period == "1mo" else 365 if period == "1y" else len(sorted_dates)
            
            for date_str in sorted_dates[:limit]:
                day_data = time_series[date_str]
                
                dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
                opens.append(float(day_data["1. open"]))
                highs.append(float(day_data["2. high"]))
                lows.append(float(day_data["3. low"]))
                closes.append(float(day_data["4. close"]))
                volumes.append(int(day_data["5. volume"]))
            
            return StockHistoricalData(
                symbol=symbol,
                dates=dates,
                opens=opens,
                highs=highs,
                lows=lows,
                closes=closes,
                volumes=volumes
            )
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Alpha Vantage historical data: {str(e)}")
            return None
    
    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """Search stocks using Alpha Vantage"""
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query
        }
        
        data = await self._make_request(params)
        if not data or "bestMatches" not in data:
            return []
        
        try:
            results = []
            for match in data["bestMatches"]:
                results.append({
                    "symbol": match["1. symbol"],
                    "name": match["2. name"],
                    "type": match["3. type"],
                    "region": match["4. region"],
                    "currency": match["8. currency"]
                })
            
            return results
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Alpha Vantage search results: {str(e)}")
            return []

class TwelveDataProvider(StockAPIProvider):
    """Twelve Data API provider"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = API_PROVIDERS["twelvedata"]["base_url"]
        self.rate_limit = API_PROVIDERS["twelvedata"]["rate_limit"]
        self.last_request_time = 0
    
    async def _make_request(self, endpoint: str, params: Dict[str, str]) -> Optional[Dict]:
        """Make rate-limited API request"""
        try:
            # Rate limiting
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time
            min_interval = 60 / self.rate_limit
            
            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)
            
            params["apikey"] = self.api_key
            url = f"{self.base_url}/{endpoint}"
            
            async with self.session.get(url, params=params) as response:
                self.last_request_time = asyncio.get_event_loop().time()
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "status" in data and data["status"] == "error":
                        logger.error(f"Twelve Data API error: {data.get('message', 'Unknown error')}")
                        return None
                    
                    return data
                else:
                    logger.error(f"Twelve Data API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Twelve Data API request error: {str(e)}")
            return None
    
    async def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get current stock quote from Twelve Data"""
        params = {"symbol": symbol}
        
        data = await self._make_request("quote", params)
        if not data:
            return None
        
        try:
            return StockQuote(
                symbol=data["symbol"],
                price=float(data["close"]),
                change=float(data["change"]),
                change_percent=float(data["percent_change"]),
                volume=int(data["volume"]),
                high=float(data["high"]),
                low=float(data["low"]),
                open=float(data["open"]),
                previous_close=float(data["previous_close"]),
                timestamp=datetime.now()
            )
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Twelve Data quote: {str(e)}")
            return None
    
    async def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[StockHistoricalData]:
        """Get historical data from Twelve Data"""
        interval_map = {
            "1mo": "1day",
            "3mo": "1day",
            "1y": "1day"
        }
        
        params = {
            "symbol": symbol,
            "interval": interval_map.get(period, "1day"),
            "outputsize": "30" if period == "1mo" else "90" if period == "3mo" else "365"
        }
        
        data = await self._make_request("time_series", params)
        if not data or "values" not in data:
            return None
        
        try:
            values = data["values"]
            
            dates = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            
            for item in values:
                dates.append(datetime.strptime(item["datetime"], "%Y-%m-%d"))
                opens.append(float(item["open"]))
                highs.append(float(item["high"]))
                lows.append(float(item["low"]))
                closes.append(float(item["close"]))
                volumes.append(int(item["volume"]))
            
            return StockHistoricalData(
                symbol=symbol,
                dates=dates,
                opens=opens,
                highs=highs,
                lows=lows,
                closes=closes,
                volumes=volumes
            )
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Twelve Data historical data: {str(e)}")
            return None
    
    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """Search stocks using Twelve Data"""
        params = {"symbol": query}
        
        data = await self._make_request("symbol_search", params)
        if not data or "data" not in data:
            return []
        
        try:
            results = []
            for item in data["data"]:
                results.append({
                    "symbol": item["symbol"],
                    "name": item["instrument_name"],
                    "type": item["instrument_type"],
                    "exchange": item["exchange"],
                    "currency": item["currency"]
                })
            
            return results
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Twelve Data search results: {str(e)}")
            return []

class YahooFinanceProvider(StockAPIProvider):
    """Yahoo Finance API provider (unofficial)"""
    
    def __init__(self, api_key: str = ""):
        super().__init__(api_key)  # Yahoo Finance doesn't require API key
        self.base_url = "https://query1.finance.yahoo.com"
        self.rate_limit = 100  # Be conservative
        self.last_request_time = 0
    
    async def _make_request(self, endpoint: str, params: Dict[str, str]) -> Optional[Dict]:
        """Make rate-limited API request"""
        try:
            # Rate limiting
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time
            min_interval = 60 / self.rate_limit
            
            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)
            
            url = f"{self.base_url}/{endpoint}"
            
            async with self.session.get(url, params=params) as response:
                self.last_request_time = asyncio.get_event_loop().time()
                
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Yahoo Finance API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Yahoo Finance API request error: {str(e)}")
            return None
    
    async def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get current stock quote from Yahoo Finance"""
        params = {
            "symbols": symbol,
            "range": "1d",
            "interval": "1d"
        }
        
        data = await self._make_request(f"v8/finance/chart/{symbol}", params)
        if not data or "chart" not in data:
            return None
        
        try:
            chart = data["chart"]["result"][0]
            meta = chart["meta"]
            
            return StockQuote(
                symbol=meta["symbol"],
                price=float(meta["regularMarketPrice"]),
                change=float(meta["regularMarketPrice"] - meta["previousClose"]),
                change_percent=float((meta["regularMarketPrice"] - meta["previousClose"]) / meta["previousClose"] * 100),
                volume=int(meta["regularMarketVolume"]),
                high=float(meta["regularMarketDayHigh"]),
                low=float(meta["regularMarketDayLow"]),
                open=float(meta["regularMarketDayOpen"]),
                previous_close=float(meta["previousClose"]),
                timestamp=datetime.now()
            )
            
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Error parsing Yahoo Finance quote: {str(e)}")
            return None
    
    async def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[StockHistoricalData]:
        """Get historical data from Yahoo Finance"""
        period_map = {
            "1mo": "1mo",
            "3mo": "3mo",
            "1y": "1y"
        }
        
        params = {
            "range": period_map.get(period, "1mo"),
            "interval": "1d"
        }
        
        data = await self._make_request(f"v8/finance/chart/{symbol}", params)
        if not data or "chart" not in data:
            return None
        
        try:
            chart = data["chart"]["result"][0]
            timestamps = chart["timestamp"]
            indicators = chart["indicators"]["quote"][0]
            
            dates = [datetime.fromtimestamp(ts) for ts in timestamps]
            opens = indicators["open"]
            highs = indicators["high"]
            lows = indicators["low"]
            closes = indicators["close"]
            volumes = indicators["volume"]
            
            # Filter out None values
            filtered_data = []
            for i in range(len(dates)):
                if all(v is not None for v in [opens[i], highs[i], lows[i], closes[i], volumes[i]]):
                    filtered_data.append((dates[i], opens[i], highs[i], lows[i], closes[i], volumes[i]))
            
            if not filtered_data:
                return None
            
            dates, opens, highs, lows, closes, volumes = zip(*filtered_data)
            
            return StockHistoricalData(
                symbol=symbol,
                dates=list(dates),
                opens=list(opens),
                highs=list(highs),
                lows=list(lows),
                closes=list(closes),
                volumes=list(volumes)
            )
            
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Error parsing Yahoo Finance historical data: {str(e)}")
            return None
    
    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """Search stocks using Yahoo Finance"""
        params = {"q": query}
        
        data = await self._make_request("v1/finance/search", params)
        if not data or "quotes" not in data:
            return []
        
        try:
            results = []
            for quote in data["quotes"]:
                if quote.get("typeDisp") == "Equity":
                    results.append({
                        "symbol": quote["symbol"],
                        "name": quote.get("longname", quote.get("shortname", "")),
                        "type": quote.get("typeDisp", ""),
                        "exchange": quote.get("exchange", ""),
                        "currency": quote.get("currency", "USD")
                    })
            
            return results
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Yahoo Finance search results: {str(e)}")
            return []

class StockDataService:
    """Main service for stock data operations"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.provider: Optional[StockAPIProvider] = None
        self.provider_name: Optional[str] = None
    
    async def initialize_provider(self) -> bool:
        """Initialize the stock API provider based on stored settings"""
        try:
            # Get API key and provider from database
            stock_api_key = retrieve_decrypted_api_key(self.db, "stock_api")
            
            if not stock_api_key:
                logger.warning("No stock API key found in database")
                return False
            
            # Get provider preference (default to alphavantage)
            from database.models import APIKey
            api_key_record = self.db.query(APIKey).filter(
                APIKey.service_name == "stock_api",
                APIKey.is_active == True
            ).first()
            
            provider_name = api_key_record.provider if api_key_record else "alphavantage"
            
            # Initialize provider
            if provider_name == "alphavantage":
                self.provider = AlphaVantageProvider(stock_api_key)
            elif provider_name == "twelvedata":
                self.provider = TwelveDataProvider(stock_api_key)
            elif provider_name == "yahoofinance":
                self.provider = YahooFinanceProvider()  # No API key needed
            else:
                logger.error(f"Unknown stock API provider: {provider_name}")
                return False
            
            self.provider_name = provider_name
            logger.info(f"Stock API provider initialized: {provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize stock API provider: {str(e)}")
            return False
    
    async def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get current stock quote"""
        if not self.provider:
            if not await self.initialize_provider():
                return None
        
        async with self.provider:
            return await self.provider.get_quote(symbol)
    
    async def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[StockHistoricalData]:
        """Get historical stock data"""
        if not self.provider:
            if not await self.initialize_provider():
                return None
        
        async with self.provider:
            return await self.provider.get_historical_data(symbol, period)
    
    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """Search for stocks"""
        if not self.provider:
            if not await self.initialize_provider():
                return []
        
        async with self.provider:
            return await self.provider.search_stocks(query)
    
    async def update_stock_data(self, symbols: List[str]) -> Dict[str, bool]:
        """Update stock data for multiple symbols"""
        results = {}
        
        for symbol in symbols:
            try:
                # Get current quote
                quote = await self.get_stock_quote(symbol)
                if quote:
                    # Store in database
                    await self._store_stock_data(quote)
                    results[symbol] = True
                else:
                    results[symbol] = False
                    
            except Exception as e:
                logger.error(f"Failed to update data for {symbol}: {str(e)}")
                results[symbol] = False
        
        return results
    
    async def _store_stock_data(self, quote: StockQuote):
        """Store stock data in database"""
        from database.models import Stock, StockPrice
        
        try:
            # Get or create stock
            stock = self.db.query(Stock).filter(Stock.symbol == quote.symbol).first()
            if not stock:
                stock = Stock(
                    symbol=quote.symbol,
                    name=f"{quote.symbol} Inc.",  # Placeholder
                    is_active=True
                )
                self.db.add(stock)
                self.db.flush()  # Get the ID
            
            # Add price data
            price_data = StockPrice(
                stock_id=stock.id,
                date=quote.timestamp,
                open_price=quote.open,
                high_price=quote.high,
                low_price=quote.low,
                close_price=quote.price,
                volume=quote.volume
            )
            self.db.add(price_data)
            self.db.commit()
            
            logger.info(f"Stored stock data for {quote.symbol}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store stock data for {quote.symbol}: {str(e)}")
            raise

def get_stock_service(db_session) -> StockDataService:
    """Get stock data service instance"""
    return StockDataService(db_session)