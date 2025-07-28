const { getSetting, updateSetting } = require('../../database/db');
const crypto = require('crypto');
const axios = require('axios');
const TelegramBot = require('node-telegram-bot-api');

// Encryption key and IV (in a real app, these would be in environment variables)
const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'your-secret-encryption-key-32-chars'; // 32 bytes
const ENCRYPTION_IV = process.env.ENCRYPTION_IV || 'your-iv-16-chars'; // 16 bytes

// Encrypt sensitive data
const encrypt = (text) => {
  const cipher = crypto.createCipheriv(
    'aes-256-cbc',
    Buffer.from(ENCRYPTION_KEY),
    Buffer.from(ENCRYPTION_IV)
  );
  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return encrypted;
};

// Decrypt sensitive data
const decrypt = (encryptedText) => {
  try {
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

// Get all settings
const getAllSettings = async (req, res, next) => {
  try {
    // Get all settings from the database
    const settings = await req.app.locals.db.allAsync('SELECT key, value, updated_at FROM settings');
    
    // Process settings before sending to client
    const processedSettings = settings.map(setting => {
      // For sensitive settings, don't return the actual value, just whether it's set
      if (['ai_api_key', 'telegram_token', 'stock_api_key'].includes(setting.key)) {
        return {
          key: setting.key,
          isSet: Boolean(setting.value),
          updated_at: setting.updated_at
        };
      }
      
      // Return non-sensitive settings as is
      return setting;
    });
    
    res.json(processedSettings);
  } catch (err) {
    next(err);
  }
};

// Update settings
const updateSettings = async (req, res, next) => {
  try {
    const { settings } = req.body;
    
    if (!settings || !Array.isArray(settings)) {
      return res.status(400).json({ error: 'Invalid settings format' });
    }
    
    const results = [];
    
    for (const setting of settings) {
      const { key, value } = setting;
      
      if (!key) {
        results.push({
          key,
          success: false,
          error: 'Missing key'
        });
        continue;
      }
      
      try {
        // Encrypt sensitive data before storing
        let valueToStore = value;
        
        if (['ai_api_key', 'telegram_token', 'stock_api_key'].includes(key) && value) {
          valueToStore = encrypt(value);
        }
        
        await updateSetting(key, valueToStore);
        
        results.push({
          key,
          success: true
        });
      } catch (err) {
        results.push({
          key,
          success: false,
          error: err.message
        });
      }
    }
    
    res.json({
      message: 'Settings updated',
      results
    });
  } catch (err) {
    next(err);
  }
};

// Test connection to external services
const testConnection = async (req, res, next) => {
  try {
    const { service } = req.body;
    
    if (!service) {
      return res.status(400).json({ error: 'Service type is required' });
    }
    
    let result = { success: false };
    
    switch (service) {
      case 'stock_api': {
        const provider = await getSetting('stock_api_provider');
        const encryptedApiKey = await getSetting('stock_api_key');
        
        if (!encryptedApiKey) {
          return res.status(400).json({ error: 'Stock API key is not set' });
        }
        
        const apiKey = decrypt(encryptedApiKey);
        
        // Test connection based on provider
        if (provider === 'alphavantage') {
          const response = await axios.get(
            `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=${apiKey}`
          );
          
          if (response.data && !response.data.hasOwnProperty('Error Message')) {
            result.success = true;
          } else {
            result.error = 'Invalid API key or API limit reached';
          }
        } else if (provider === 'twelvedata') {
          const response = await axios.get(
            `https://api.twelvedata.com/time_series?symbol=AAPL&interval=1day&apikey=${apiKey}&source=docs`
          );
          
          if (response.data && !response.data.hasOwnProperty('code')) {
            result.success = true;
          } else {
            result.error = response.data.message || 'API connection failed';
          }
        } else {
          result.error = 'Unsupported API provider';
        }
        break;
      }
      
      case 'telegram': {
        const encryptedToken = await getSetting('telegram_token');
        
        if (!encryptedToken) {
          return res.status(400).json({ error: 'Telegram token is not set' });
        }
        
        const token = decrypt(encryptedToken);
        
        try {
          // Create a bot instance and get bot info
          const bot = new TelegramBot(token, { polling: false });
          const botInfo = await bot.getMe();
          
          if (botInfo && botInfo.id) {
            result = {
              success: true,
              botInfo: {
                id: botInfo.id,
                username: botInfo.username,
                first_name: botInfo.first_name
              }
            };
          }
        } catch (err) {
          result.error = 'Invalid Telegram token';
        }
        break;
      }
      
      case 'ai_api': {
        const encryptedApiKey = await getSetting('ai_api_key');
        
        if (!encryptedApiKey) {
          return res.status(400).json({ error: 'AI API key is not set' });
        }
        
        // Since we don't have a specific AI API implementation yet,
        // we'll just return success if the key exists
        result.success = true;
        result.message = 'AI API key is set';
        break;
      }
      
      default:
        return res.status(400).json({ error: 'Unsupported service type' });
    }
    
    res.json(result);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  getAllSettings,
  updateSettings,
  testConnection
};