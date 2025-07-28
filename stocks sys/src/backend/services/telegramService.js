const TelegramBot = require('node-telegram-bot-api');
const { getSetting } = require('../database/db');
const crypto = require('crypto');

// Decrypt sensitive data (same as in other services)
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

// Get or create Telegram bot instance
let bot = null;

const getBot = async () => {
  if (bot) return bot;
  
  const encryptedToken = await getSetting('telegram_token');
  
  if (!encryptedToken) {
    throw new Error('Telegram token is not set');
  }
  
  const token = decrypt(encryptedToken);
  
  if (!token) {
    throw new Error('Failed to decrypt Telegram token');
  }
  
  bot = new TelegramBot(token, { polling: false });
  return bot;
};

// Send a message via Telegram
const sendMessage = async (message) => {
  try {
    const bot = await getBot();
    const chatId = await getSetting('telegram_chat_id');
    
    if (!chatId) {
      throw new Error('Telegram chat ID is not set');
    }
    
    const result = await bot.sendMessage(chatId, message, { parse_mode: 'Markdown' });
    return result;
  } catch (err) {
    console.error('Error sending Telegram message:', err);
    throw err;
  }
};

// Send a stock update message
const sendStockUpdate = async (symbol, data) => {
  try {
    const message = formatStockUpdateMessage(symbol, data);
    return await sendMessage(message);
  } catch (err) {
    console.error(`Error sending stock update for ${symbol}:`, err);
    throw err;
  }
};

// Format a stock update message
const formatStockUpdateMessage = (symbol, data) => {
  const { close, change, changePercent } = data;
  const direction = change >= 0 ? '📈' : '📉';
  const changeSign = change >= 0 ? '+' : '';
  
  return `*Stock Update: ${symbol}* ${direction}\n\n` +
    `Current Price: $${close.toFixed(2)}\n` +
    `Change: ${changeSign}$${change.toFixed(2)} (${changeSign}${changePercent.toFixed(2)}%)\n\n` +
    `Updated: ${new Date().toLocaleString()}`;
};

// Send a daily summary message
const sendDailySummary = async (stocks) => {
  try {
    const message = formatDailySummaryMessage(stocks);
    return await sendMessage(message);
  } catch (err) {
    console.error('Error sending daily summary:', err);
    throw err;
  }
};

// Format a daily summary message
const formatDailySummaryMessage = (stocks) => {
  let message = `*Daily Stock Summary*\n\n`;
  
  for (const stock of stocks) {
    const direction = stock.change >= 0 ? '📈' : '📉';
    const changeSign = stock.change >= 0 ? '+' : '';
    
    message += `*${stock.symbol}*: $${stock.close.toFixed(2)} ${direction} ${changeSign}${stock.changePercent.toFixed(2)}%\n`;
  }
  
  message += `\nDate: ${new Date().toLocaleDateString()}`;
  
  return message;
};

// Register a new chat for notifications
const registerChat = async (chatId) => {
  try {
    await getSetting('telegram_chat_id', chatId.toString());
    return true;
  } catch (err) {
    console.error('Error registering chat:', err);
    throw err;
  }
};

module.exports = {
  sendMessage,
  sendStockUpdate,
  sendDailySummary,
  registerChat
};