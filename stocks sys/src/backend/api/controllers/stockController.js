const { db } = require('../../database/db');
const stockService = require('../../services/stockService');

// Get all stocks from the database
const getAllStocks = async (req, res, next) => {
  try {
    const stocks = await db.allAsync('SELECT * FROM stocks ORDER BY symbol');
    res.json(stocks);
  } catch (err) {
    next(err);
  }
};

// Get a specific stock by symbol
const getStockBySymbol = async (req, res, next) => {
  try {
    const { symbol } = req.params;
    
    // Get stock info from database
    const stock = await db.getAsync('SELECT * FROM stocks WHERE symbol = ?', [symbol]);
    
    if (!stock) {
      return res.status(404).json({ error: 'Stock not found' });
    }
    
    // Get latest price
    const latestPrice = await db.getAsync(
      'SELECT * FROM historical_prices WHERE symbol = ? ORDER BY date DESC LIMIT 1',
      [symbol]
    );
    
    // Combine stock info with latest price
    const result = {
      ...stock,
      latestPrice: latestPrice || null
    };
    
    res.json(result);
  } catch (err) {
    next(err);
  }
};

// Get historical price data for a stock
const getStockHistory = async (req, res, next) => {
  try {
    const { symbol } = req.params;
    const { period = '1m', interval = 'daily' } = req.query;
    
    // Validate that the stock exists
    const stockExists = await db.getAsync('SELECT 1 FROM stocks WHERE symbol = ?', [symbol]);
    
    if (!stockExists) {
      return res.status(404).json({ error: 'Stock not found' });
    }
    
    // Calculate date range based on period
    const endDate = new Date();
    let startDate = new Date();
    
    switch (period) {
      case '1w':
        startDate.setDate(endDate.getDate() - 7);
        break;
      case '1m':
        startDate.setMonth(endDate.getMonth() - 1);
        break;
      case '3m':
        startDate.setMonth(endDate.getMonth() - 3);
        break;
      case '6m':
        startDate.setMonth(endDate.getMonth() - 6);
        break;
      case '1y':
        startDate.setFullYear(endDate.getFullYear() - 1);
        break;
      case '5y':
        startDate.setFullYear(endDate.getFullYear() - 5);
        break;
      default:
        startDate.setMonth(endDate.getMonth() - 1); // Default to 1 month
    }
    
    // Format dates for SQL query
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    // Query historical prices
    const historicalPrices = await db.allAsync(
      'SELECT * FROM historical_prices WHERE symbol = ? AND date BETWEEN ? AND ? ORDER BY date',
      [symbol, startDateStr, endDateStr]
    );
    
    // Format the response
    const result = {
      symbol,
      period,
      interval,
      data: historicalPrices
    };
    
    res.json(result);
  } catch (err) {
    next(err);
  }
};

// Refresh stock data from the API
const refreshStockData = async (req, res, next) => {
  try {
    const { symbols } = req.body;
    
    if (!symbols || !Array.isArray(symbols) || symbols.length === 0) {
      return res.status(400).json({ error: 'Please provide an array of stock symbols' });
    }
    
    // Call the stock service to fetch fresh data
    const results = await Promise.all(
      symbols.map(symbol => stockService.fetchStockData(symbol))
    );
    
    res.json({
      message: 'Stock data refreshed successfully',
      results
    });
  } catch (err) {
    next(err);
  }
};

module.exports = {
  getAllStocks,
  getStockBySymbol,
  getStockHistory,
  refreshStockData
};