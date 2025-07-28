const axios = require('axios');
const { db, getSetting } = require('../database/db');
const crypto = require('crypto');

// Decrypt sensitive data (same as in other controllers)
const decrypt = (encryptedText) => {
  try {
    const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'your-secret-encryption-key-32-chars';
    const ENCRYPTION_IV = process.env.ENCRYPTION_IV || 'your-iv-16-chars';
    
    const decipher = crypto.createDecipheriv(
      'aes-256-cbc',
      Buffer.from(ENCRYPTION_KEY),
      Buffer.from(ENCRYPTION_IV)
    );
    let decrypted = decipher.update(encryptedText, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  } catch (err) {
    console.error('Decryption error:', err);
    return null;
  }
};

// Fetch stock data from the API
const fetchStockData = async (symbol) => {
  try {
    // Get API provider and key from settings
    const provider = await getSetting('stock_api_provider') || 'alphavantage';
    const encryptedApiKey = await getSetting('stock_api_key');
    
    if (!encryptedApiKey) {
      throw new Error('Stock API key is not set');
    }
    
    const apiKey = decrypt(encryptedApiKey);
    
    if (!apiKey) {
      throw new Error('Failed to decrypt API key');
    }
    
    // Fetch data based on the provider
    let stockData;
    
    switch (provider) {
      case 'alphavantage':
        stockData = await fetchFromAlphaVantage(symbol, apiKey);
        break;
      case 'twelvedata':
        stockData = await fetchFromTwelveData(symbol, apiKey);
        break;
      case 'yahoofinance':
        stockData = await fetchFromYahooFinance(symbol);
        break;
      default:
        throw new Error(`Unsupported API provider: ${provider}`);
    }
    
    // Save the data to the database
    await saveStockData(stockData);
    
    return stockData;
  } catch (err) {
    console.error(`Error fetching stock data for ${symbol}:`, err);
    throw err;
  }
};

// Fetch from Alpha Vantage API
const fetchFromAlphaVantage = async (symbol, apiKey) => {
  try {
    // Fetch company overview
    const overviewResponse = await axios.get(
      `https://www.alphavantage.co/query?function=OVERVIEW&symbol=${symbol}&apikey=${apiKey}`
    );
    
    if (overviewResponse.data && overviewResponse.data.Symbol) {
      const overview = overviewResponse.data;
      
      // Fetch daily time series
      const timeSeriesResponse = await axios.get(
        `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=${symbol}&outputsize=compact&apikey=${apiKey}`
      );
      
      if (timeSeriesResponse.data && timeSeriesResponse.data['Time Series (Daily)']) {
        const timeSeries = timeSeriesResponse.data['Time Series (Daily)'];
        
        // Process the data
        const stockInfo = {
          symbol: overview.Symbol,
          name: overview.Name,
          exchange: overview.Exchange,
          sector: overview.Sector,
          industry: overview.Industry,
        };
        
        const historicalPrices = [];
        
        for (const [date, data] of Object.entries(timeSeries)) {
          historicalPrices.push({
            date,
            open: parseFloat(data['1. open']),
            high: parseFloat(data['2. high']),
            low: parseFloat(data['3. low']),
            close: parseFloat(data['4. close']),
            volume: parseInt(data['5. volume'], 10),
          });
        }
        
        return {
          stockInfo,
          historicalPrices,
        };
      }
    }
    
    throw new Error('Invalid response from Alpha Vantage API');
  } catch (err) {
    console.error('Error fetching from Alpha Vantage:', err);
    throw err;
  }
};

// Fetch from Twelve Data API
const fetchFromTwelveData = async (symbol, apiKey) => {
  try {
    // Fetch stock info
    const stockInfoResponse = await axios.get(
      `https://api.twelvedata.com/stocks?symbol=${symbol}&source=docs&apikey=${apiKey}`
    );
    
    if (stockInfoResponse.data && stockInfoResponse.data.data && stockInfoResponse.data.data.length > 0) {
      const stockInfo = stockInfoResponse.data.data[0];
      
      // Fetch time series
      const timeSeriesResponse = await axios.get(
        `https://api.twelvedata.com/time_series?symbol=${symbol}&interval=1day&outputsize=30&apikey=${apiKey}`
      );
      
      if (timeSeriesResponse.data && timeSeriesResponse.data.values) {
        const timeSeries = timeSeriesResponse.data.values;
        
        // Process the data
        const processedStockInfo = {
          symbol: stockInfo.symbol,
          name: stockInfo.name,
          exchange: stockInfo.exchange,
          sector: '', // Not provided by Twelve Data
          industry: '', // Not provided by Twelve Data
        };
        
        const historicalPrices = timeSeries.map(data => ({
          date: data.datetime,
          open: parseFloat(data.open),
          high: parseFloat(data.high),
          low: parseFloat(data.low),
          close: parseFloat(data.close),
          volume: parseInt(data.volume, 10),
        }));
        
        return {
          stockInfo: processedStockInfo,
          historicalPrices,
        };
      }
    }
    
    throw new Error('Invalid response from Twelve Data API');
  } catch (err) {
    console.error('Error fetching from Twelve Data:', err);
    throw err;
  }
};

// Fetch from Yahoo Finance (note: this is a placeholder as Yahoo Finance requires a different approach)
const fetchFromYahooFinance = async (symbol) => {
  // In a real app, you would use a library like yahoo-finance2 or a third-party API
  // For now, we'll just return dummy data
  
  const stockInfo = {
    symbol,
    name: `${symbol} Inc.`,
    exchange: 'NASDAQ',
    sector: 'Technology',
    industry: 'Software',
  };
  
  const historicalPrices = [];
  const today = new Date();
  let basePrice = 100 + Math.random() * 100;
  
  // Generate 30 days of dummy data
  for (let i = 29; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(today.getDate() - i);
    const dateStr = date.toISOString().split('T')[0];
    
    // Add some randomness to price
    basePrice = basePrice + (Math.random() - 0.5) * 5;
    const open = basePrice - Math.random() * 2;
    const close = basePrice;
    const high = Math.max(open, close) + Math.random() * 3;
    const low = Math.min(open, close) - Math.random() * 3;
    
    historicalPrices.push({
      date: dateStr,
      open,
      high,
      low,
      close,
      volume: Math.floor(Math.random() * 10000000) + 1000000,
    });
  }
  
  return {
    stockInfo,
    historicalPrices,
  };
};

// Save stock data to the database
const saveStockData = async ({ stockInfo, historicalPrices }) => {
  try {
    // Save or update stock info
    await db.runAsync(
      `INSERT OR REPLACE INTO stocks 
       (symbol, name, exchange, sector, industry, updated_at) 
       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`,
      [stockInfo.symbol, stockInfo.name, stockInfo.exchange, stockInfo.sector, stockInfo.industry]
    );
    
    // Save historical prices
    for (const price of historicalPrices) {
      await db.runAsync(
        `INSERT OR REPLACE INTO historical_prices 
         (symbol, date, open, high, low, close, volume) 
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
        [stockInfo.symbol, price.date, price.open, price.high, price.low, price.close, price.volume]
      );
    }
    
    return true;
  } catch (err) {
    console.error('Error saving stock data:', err);
    throw err;
  }
};

module.exports = {
  fetchStockData,
};