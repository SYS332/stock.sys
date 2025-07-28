"""
AI Prediction Service for Stock Analysis
Supports multiple AI providers: OpenAI, Claude, Custom models
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from abc import ABC, abstractmethod
import numpy as np

from config import get_settings, AI_PROVIDERS
from services.encryption import retrieve_decrypted_api_key
from database.models import Stock, StockPrice, StockMetric, Prediction

logger = logging.getLogger(__name__)

@dataclass
class PredictionRequest:
    """Prediction request data structure"""
    symbol: str
    timeframe: str  # 'short', 'medium', 'long'
    historical_data: List[Dict[str, Any]]
    technical_indicators: Dict[str, float]
    market_context: Optional[Dict[str, Any]] = None

@dataclass
class PredictionResult:
    """AI prediction result structure"""
    symbol: str
    timeframe: str
    prediction_type: str  # 'bullish', 'bearish', 'neutral'
    confidence: float  # 0.0 to 1.0
    target_price: Optional[float]
    reasoning: str
    signals_used: List[str]
    model_version: str
    timestamp: datetime

class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def generate_prediction(self, request: PredictionRequest) -> Optional[PredictionResult]:
        """Generate stock prediction"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection"""
        pass

class OpenAIProvider(AIProvider):
    """OpenAI GPT provider for stock predictions"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, model)
        self.base_url = AI_PROVIDERS["openai"]["base_url"]
        self.available_models = AI_PROVIDERS["openai"]["models"]
        
        if model not in self.available_models:
            logger.warning(f"Model {model} not in available models, using default")
            self.model = AI_PROVIDERS["openai"]["default_model"]
    
    async def generate_prediction(self, request: PredictionRequest) -> Optional[PredictionResult]:
        """Generate prediction using OpenAI GPT"""
        try:
            # Prepare the prompt
            prompt = self._create_prediction_prompt(request)
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert stock market analyst with deep knowledge of technical analysis, fundamental analysis, and market trends. Provide detailed, data-driven stock predictions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3,  # Lower temperature for more consistent predictions
                "response_format": {"type": "json_object"}
            }
            
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_openai_response(data, request)
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"OpenAI prediction error: {str(e)}")
            return None
    
    def _create_prediction_prompt(self, request: PredictionRequest) -> str:
        """Create prediction prompt for OpenAI"""
        timeframe_map = {
            "short": "7 days",
            "medium": "30 days", 
            "long": "90 days"
        }
        
        prompt = f"""
        Analyze the stock {request.symbol} and provide a {timeframe_map.get(request.timeframe, '30 days')} prediction.

        Historical Price Data (last 30 days):
        {json.dumps(request.historical_data[-30:], indent=2)}

        Technical Indicators:
        {json.dumps(request.technical_indicators, indent=2)}

        Please provide your analysis in the following JSON format:
        {{
            "prediction_type": "bullish|bearish|neutral",
            "confidence": 0.0-1.0,
            "target_price": estimated_price_or_null,
            "reasoning": "detailed explanation of your analysis",
            "key_signals": ["signal1", "signal2", "signal3"],
            "risk_factors": ["risk1", "risk2"],
            "support_levels": [price1, price2],
            "resistance_levels": [price1, price2]
        }}

        Consider:
        1. Technical indicators (RSI, MACD, Moving Averages)
        2. Price trends and patterns
        3. Volume analysis
        4. Support and resistance levels
        5. Market momentum
        6. Risk assessment

        Be specific about your reasoning and confidence level.
        """
        
        return prompt
    
    def _parse_openai_response(self, data: Dict, request: PredictionRequest) -> Optional[PredictionResult]:
        """Parse OpenAI API response"""
        try:
            content = data["choices"][0]["message"]["content"]
            prediction_data = json.loads(content)
            
            return PredictionResult(
                symbol=request.symbol,
                timeframe=request.timeframe,
                prediction_type=prediction_data.get("prediction_type", "neutral"),
                confidence=float(prediction_data.get("confidence", 0.5)),
                target_price=prediction_data.get("target_price"),
                reasoning=prediction_data.get("reasoning", ""),
                signals_used=prediction_data.get("key_signals", []),
                model_version=self.model,
                timestamp=datetime.utcnow()
            )
            
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing OpenAI response: {str(e)}")
            return None
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test OpenAI API connection"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
            
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    return {
                        "status": "success",
                        "message": "OpenAI API connection successful",
                        "model": self.model
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "failed",
                        "message": f"OpenAI API error: {error_text}"
                    }
                    
        except Exception as e:
            return {
                "status": "failed",
                "message": f"OpenAI connection test failed: {str(e)}"
            }

class ClaudeProvider(AIProvider):
    """Anthropic Claude provider for stock predictions"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        super().__init__(api_key, model)
        self.base_url = AI_PROVIDERS["claude"]["base_url"]
        self.available_models = AI_PROVIDERS["claude"]["models"]
        
        if model not in self.available_models:
            logger.warning(f"Model {model} not in available models, using default")
            self.model = AI_PROVIDERS["claude"]["default_model"]
    
    async def generate_prediction(self, request: PredictionRequest) -> Optional[PredictionResult]:
        """Generate prediction using Claude"""
        try:
            # Prepare the prompt
            prompt = self._create_prediction_prompt(request)
            
            # Make API request
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            async with self.session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_claude_response(data, request)
                else:
                    error_text = await response.text()
                    logger.error(f"Claude API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Claude prediction error: {str(e)}")
            return None
    
    def _create_prediction_prompt(self, request: PredictionRequest) -> str:
        """Create prediction prompt for Claude"""
        timeframe_map = {
            "short": "7 days",
            "medium": "30 days",
            "long": "90 days"
        }
        
        prompt = f"""
        As an expert stock analyst, analyze {request.symbol} for a {timeframe_map.get(request.timeframe, '30 days')} prediction.

        Historical Data: {json.dumps(request.historical_data[-30:], indent=2)}
        Technical Indicators: {json.dumps(request.technical_indicators, indent=2)}

        Provide analysis in JSON format:
        {{
            "prediction_type": "bullish|bearish|neutral",
            "confidence": 0.0-1.0,
            "target_price": number_or_null,
            "reasoning": "detailed analysis",
            "key_signals": ["signal1", "signal2"],
            "risk_assessment": "risk analysis"
        }}

        Focus on technical analysis, price patterns, and market indicators.
        """
        
        return prompt
    
    def _parse_claude_response(self, data: Dict, request: PredictionRequest) -> Optional[PredictionResult]:
        """Parse Claude API response"""
        try:
            content = data["content"][0]["text"]
            
            # Extract JSON from response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                prediction_data = json.loads(json_str)
                
                return PredictionResult(
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    prediction_type=prediction_data.get("prediction_type", "neutral"),
                    confidence=float(prediction_data.get("confidence", 0.5)),
                    target_price=prediction_data.get("target_price"),
                    reasoning=prediction_data.get("reasoning", ""),
                    signals_used=prediction_data.get("key_signals", []),
                    model_version=self.model,
                    timestamp=datetime.utcnow()
                )
            else:
                logger.error("No JSON found in Claude response")
                return None
                
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Claude response: {str(e)}")
            return None
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Claude API connection"""
        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hello"}]
            }
            
            async with self.session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    return {
                        "status": "success",
                        "message": "Claude API connection successful",
                        "model": self.model
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "failed",
                        "message": f"Claude API error: {error_text}"
                    }
                    
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Claude connection test failed: {str(e)}"
            }

class CustomModelProvider(AIProvider):
    """Custom model provider for local or custom AI models"""
    
    def __init__(self, api_key: str = "", model: str = "custom-model", base_url: str = "http://localhost:8080/v1"):
        super().__init__(api_key, model)
        self.base_url = base_url
    
    async def generate_prediction(self, request: PredictionRequest) -> Optional[PredictionResult]:
        """Generate prediction using custom model"""
        try:
            # For custom models, implement your own logic here
            # This is a placeholder implementation
            
            # Simple rule-based prediction as fallback
            return self._generate_rule_based_prediction(request)
            
        except Exception as e:
            logger.error(f"Custom model prediction error: {str(e)}")
            return None
    
    def _generate_rule_based_prediction(self, request: PredictionRequest) -> PredictionResult:
        """Generate rule-based prediction as fallback"""
        try:
            indicators = request.technical_indicators
            
            # Simple scoring system
            bullish_score = 0
            bearish_score = 0
            
            # RSI analysis
            rsi = indicators.get('rsi', 50)
            if rsi < 30:
                bullish_score += 2  # Oversold
            elif rsi > 70:
                bearish_score += 2  # Overbought
            
            # MACD analysis
            macd = indicators.get('macd', 0)
            if macd > 0:
                bullish_score += 1
            else:
                bearish_score += 1
            
            # Moving average analysis
            ma_20 = indicators.get('moving_avg_20', 0)
            ma_50 = indicators.get('moving_avg_50', 0)
            
            if ma_20 > ma_50:
                bullish_score += 1
            else:
                bearish_score += 1
            
            # Determine prediction
            if bullish_score > bearish_score:
                prediction_type = "bullish"
                confidence = min(0.8, bullish_score / 5.0)
            elif bearish_score > bullish_score:
                prediction_type = "bearish"
                confidence = min(0.8, bearish_score / 5.0)
            else:
                prediction_type = "neutral"
                confidence = 0.5
            
            # Estimate target price (simple calculation)
            current_price = request.historical_data[-1].get('close', 100) if request.historical_data else 100
            
            if prediction_type == "bullish":
                target_price = current_price * (1 + confidence * 0.1)
            elif prediction_type == "bearish":
                target_price = current_price * (1 - confidence * 0.1)
            else:
                target_price = current_price
            
            signals_used = []
            if rsi < 30 or rsi > 70:
                signals_used.append(f"RSI: {rsi:.1f}")
            if macd != 0:
                signals_used.append(f"MACD: {'Positive' if macd > 0 else 'Negative'}")
            if ma_20 != ma_50:
                signals_used.append(f"MA Cross: {'Bullish' if ma_20 > ma_50 else 'Bearish'}")
            
            reasoning = f"Rule-based analysis using technical indicators. "
            reasoning += f"Bullish signals: {bullish_score}, Bearish signals: {bearish_score}. "
            reasoning += f"Key factors: {', '.join(signals_used) if signals_used else 'Limited signals available'}."
            
            return PredictionResult(
                symbol=request.symbol,
                timeframe=request.timeframe,
                prediction_type=prediction_type,
                confidence=confidence,
                target_price=target_price,
                reasoning=reasoning,
                signals_used=signals_used,
                model_version="rule-based-v1.0",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Rule-based prediction error: {str(e)}")
            # Return neutral prediction as ultimate fallback
            return PredictionResult(
                symbol=request.symbol,
                timeframe=request.timeframe,
                prediction_type="neutral",
                confidence=0.3,
                target_price=None,
                reasoning="Fallback prediction due to analysis error",
                signals_used=[],
                model_version="fallback-v1.0",
                timestamp=datetime.utcnow()
            )
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test custom model connection"""
        try:
            # For custom models, implement your own connection test
            return {
                "status": "success",
                "message": "Custom model connection successful (rule-based fallback)",
                "model": self.model
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Custom model connection test failed: {str(e)}"
            }

class AIPredictionService:
    """Main service for AI predictions"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.provider: Optional[AIProvider] = None
        self.provider_name: Optional[str] = None
    
    async def initialize_provider(self) -> bool:
        """Initialize the AI provider based on stored settings"""
        try:
            # Get AI API key and provider from database
            ai_api_key = retrieve_decrypted_api_key(self.db, "ai_api")
            
            if not ai_api_key:
                logger.warning("No AI API key found, using rule-based fallback")
                self.provider = CustomModelProvider()
                self.provider_name = "custom"
                return True
            
            # Get provider preference
            from database.models import APIKey
            api_key_record = self.db.query(APIKey).filter(
                APIKey.service_name == "ai_api",
                APIKey.is_active == True
            ).first()
            
            provider_name = api_key_record.provider if api_key_record else "openai"
            
            # Initialize provider
            if provider_name == "openai":
                self.provider = OpenAIProvider(ai_api_key)
            elif provider_name == "claude":
                self.provider = ClaudeProvider(ai_api_key)
            elif provider_name == "custom":
                self.provider = CustomModelProvider(ai_api_key)
            else:
                logger.error(f"Unknown AI provider: {provider_name}")
                # Fallback to custom provider
                self.provider = CustomModelProvider()
                provider_name = "custom"
            
            self.provider_name = provider_name
            logger.info(f"AI provider initialized: {provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI provider: {str(e)}")
            # Fallback to custom provider
            self.provider = CustomModelProvider()
            self.provider_name = "custom"
            return True
    
    async def generate_prediction(
        self, 
        symbol: str, 
        timeframe: str = "medium"
    ) -> Optional[PredictionResult]:
        """Generate AI prediction for a stock"""
        if not self.provider:
            if not await self.initialize_provider():
                return None
        
        try:
            # Prepare prediction request
            request = await self._prepare_prediction_request(symbol, timeframe)
            if not request:
                return None
            
            # Generate prediction
            async with self.provider:
                prediction = await self.provider.generate_prediction(request)
            
            if prediction:
                # Store prediction in database
                await self._store_prediction(prediction)
                logger.info(f"Generated prediction for {symbol} ({timeframe}): {prediction.prediction_type}")
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error generating prediction for {symbol}: {str(e)}")
            return None
    
    async def _prepare_prediction_request(
        self, 
        symbol: str, 
        timeframe: str
    ) -> Optional[PredictionRequest]:
        """Prepare prediction request with historical data and indicators"""
        try:
            from database.models import get_stock_by_symbol, get_latest_metrics
            
            # Get stock
            stock = get_stock_by_symbol(self.db, symbol)
            if not stock:
                logger.error(f"Stock {symbol} not found")
                return None
            
            # Get historical price data (last 60 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            prices = self.db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            ).order_by(StockPrice.date.asc()).all()
            
            if not prices:
                logger.error(f"No historical data found for {symbol}")
                return None
            
            # Convert to list of dictionaries
            historical_data = []
            for price in prices:
                historical_data.append({
                    "date": price.date.isoformat(),
                    "open": price.open_price,
                    "high": price.high_price,
                    "low": price.low_price,
                    "close": price.close_price,
                    "volume": price.volume
                })
            
            # Get latest technical indicators
            latest_metrics = get_latest_metrics(self.db, stock.id)
            technical_indicators = {}
            
            if latest_metrics:
                technical_indicators = {
                    "rsi": latest_metrics.rsi or 50.0,
                    "macd": latest_metrics.macd or 0.0,
                    "macd_signal": latest_metrics.macd_signal or 0.0,
                    "moving_avg_20": latest_metrics.moving_avg_20 or 0.0,
                    "moving_avg_50": latest_metrics.moving_avg_50 or 0.0,
                    "moving_avg_200": latest_metrics.moving_avg_200 or 0.0,
                    "bollinger_upper": latest_metrics.bollinger_upper or 0.0,
                    "bollinger_lower": latest_metrics.bollinger_lower or 0.0,
                    "volatility": latest_metrics.volatility or 0.0
                }
            else:
                # Calculate basic indicators from price data
                technical_indicators = self._calculate_basic_indicators(historical_data)
            
            return PredictionRequest(
                symbol=symbol,
                timeframe=timeframe,
                historical_data=historical_data,
                technical_indicators=technical_indicators
            )
            
        except Exception as e:
            logger.error(f"Error preparing prediction request: {str(e)}")
            return None
    
    def _calculate_basic_indicators(self, historical_data: List[Dict]) -> Dict[str, float]:
        """Calculate basic technical indicators from price data"""
        try:
            if len(historical_data) < 20:
                return {}
            
            closes = [float(d["close"]) for d in historical_data]
            
            # Simple moving averages
            ma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
            ma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else closes[-1]
            
            # Simple RSI calculation (simplified)
            if len(closes) >= 14:
                gains = []
                losses = []
                for i in range(1, min(15, len(closes))):
                    change = closes[i] - closes[i-1]
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))
                
                avg_gain = sum(gains) / len(gains) if gains else 0
                avg_loss = sum(losses) / len(losses) if losses else 0
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 50
            
            return {
                "rsi": rsi,
                "macd": 0.0,  # Placeholder
                "moving_avg_20": ma_20,
                "moving_avg_50": ma_50,
                "moving_avg_200": closes[-1],  # Placeholder
                "volatility": 0.0  # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return {}
    
    async def _store_prediction(self, prediction: PredictionResult):
        """Store prediction in database"""
        try:
            from database.models import get_stock_by_symbol
            
            stock = get_stock_by_symbol(self.db, prediction.symbol)
            if not stock:
                logger.error(f"Cannot store prediction: stock {prediction.symbol} not found")
                return
            
            # Create prediction record
            prediction_record = Prediction(
                stock_id=stock.id,
                prediction_date=prediction.timestamp,
                timeframe=prediction.timeframe,
                prediction_type=prediction.prediction_type,
                confidence=prediction.confidence,
                target_price=prediction.target_price,
                ai_provider=self.provider_name,
                model_version=prediction.model_version,
                reasoning=prediction.reasoning,
                signals_used=json.dumps(prediction.signals_used),
                is_evaluated=False
            )
            
            self.db.add(prediction_record)
            self.db.commit()
            
            logger.info(f"Stored prediction for {prediction.symbol}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing prediction: {str(e)}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test AI provider connection"""
        if not self.provider:
            if not await self.initialize_provider():
                return {
                    "status": "failed",
                    "message": "Failed to initialize AI provider"
                }
        
        async with self.provider:
            return await self.provider.test_connection()

def get_ai_prediction_service(db_session) -> AIPredictionService:
    """Get AI prediction service instance"""
    return AIPredictionService(db_session)