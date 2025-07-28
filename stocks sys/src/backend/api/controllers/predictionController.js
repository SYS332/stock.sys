const { db, getSetting } = require('../../database/db');
const crypto = require('crypto');

// Decrypt sensitive data (same as in settingsController)
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

// Get predictions for a stock
const getPredictions = async (req, res, next) => {
  try {
    const { symbol } = req.params;
    const { timeframe } = req.query;
    
    // Build the query
    let query = 'SELECT * FROM predictions WHERE symbol = ?';
    const params = [symbol];
    
    if (timeframe) {
      query += ' AND timeframe = ?';
      params.push(timeframe);
    }
    
    query += ' ORDER BY date DESC, timeframe ASC';
    
    // Execute the query
    const predictions = await db.allAsync(query, params);
    
    res.json(predictions);
  } catch (err) {
    next(err);
  }
};

// Generate a new prediction
const generatePrediction = async (req, res, next) => {
  try {
    const { symbol, timeframe } = req.body;
    
    if (!symbol) {
      return res.status(400).json({ error: 'Stock symbol is required' });
    }
    
    if (!timeframe || !['short', 'medium', 'long'].includes(timeframe)) {
      return res.status(400).json({ error: 'Valid timeframe is required (short, medium, or long)' });
    }
    
    // Check if AI API key is set
    const encryptedApiKey = await getSetting('ai_api_key');
    
    if (!encryptedApiKey) {
      return res.status(400).json({ error: 'AI API key is not set' });
    }
    
    // Decrypt the API key
    const apiKey = decrypt(encryptedApiKey);
    
    if (!apiKey) {
      return res.status(500).json({ error: 'Failed to decrypt AI API key' });
    }
    
    // In a real app, you would call the AI API here
    // For now, we'll generate a dummy prediction
    
    // Get the latest stock data
    const latestPrice = await db.getAsync(
      'SELECT * FROM historical_prices WHERE symbol = ? ORDER BY date DESC LIMIT 1',
      [symbol]
    );
    
    if (!latestPrice) {
      return res.status(404).json({ error: 'No historical data found for this stock' });
    }
    
    // Generate a dummy prediction
    const currentPrice = latestPrice.close;
    let predictionType, confidence, targetPrice, daysAhead;
    
    // Randomize the prediction
    const random = Math.random();
    
    if (random > 0.6) {
      predictionType = 'bullish';
      confidence = (Math.random() * 30 + 60).toFixed(2); // 60-90%
      targetPrice = (currentPrice * (1 + Math.random() * 0.2)).toFixed(2); // Up to 20% increase
    } else if (random > 0.3) {
      predictionType = 'neutral';
      confidence = (Math.random() * 20 + 50).toFixed(2); // 50-70%
      targetPrice = (currentPrice * (1 + (Math.random() - 0.5) * 0.1)).toFixed(2); // -5% to +5%
    } else {
      predictionType = 'bearish';
      confidence = (Math.random() * 30 + 60).toFixed(2); // 60-90%
      targetPrice = (currentPrice * (1 - Math.random() * 0.15)).toFixed(2); // Up to 15% decrease
    }
    
    // Set timeframe in days
    switch (timeframe) {
      case 'short':
        daysAhead = 7; // 1 week
        break;
      case 'medium':
        daysAhead = 30; // 1 month
        break;
      case 'long':
        daysAhead = 90; // 3 months
        break;
    }
    
    // Calculate target date
    const today = new Date();
    const targetDate = new Date(today);
    targetDate.setDate(today.getDate() + daysAhead);
    const targetDateStr = targetDate.toISOString().split('T')[0];
    
    // Save the prediction to the database
    const result = await db.runAsync(
      `INSERT INTO predictions 
       (symbol, date, prediction_type, timeframe, prediction, confidence, target_price) 
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [symbol, today.toISOString().split('T')[0], timeframe, targetDateStr, predictionType, confidence, targetPrice]
    );
    
    // Return the prediction
    const prediction = {
      id: result.lastID,
      symbol,
      date: today.toISOString().split('T')[0],
      prediction_type: timeframe,
      timeframe: targetDateStr,
      prediction: predictionType,
      confidence,
      target_price: targetPrice,
      created_at: new Date().toISOString()
    };
    
    res.json(prediction);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  getPredictions,
  generatePrediction
};