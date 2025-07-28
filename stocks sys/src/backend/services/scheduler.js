const cron = require('node-cron');
const { getSetting } = require('../database/db');
const stockService = require('./stockService');
const telegramService = require('./telegramService');

// Initialize scheduled jobs
const initScheduledJobs = () => {
  console.log('Initializing scheduled jobs...');
  
  // Schedule daily stock data update - run at 6:00 AM every day
  cron.schedule('0 6 * * *', async () => {
    console.log('Running scheduled stock data update...');
    await updateStockData();
  });
  
  // Schedule daily notifications - run at 8:00 AM every day
  cron.schedule('0 8 * * *', async () => {
    console.log('Sending daily stock notifications...');
    await sendDailyNotifications();
  });
  
  // Schedule weekly database backup - run at 1:00 AM every Sunday
  cron.schedule('0 1 * * 0', async () => {
    console.log('Running weekly database backup...');
    await backupDatabase();
  });
  
  console.log('Scheduled jobs initialized');
};

// Update stock data for all tracked stocks
const updateStockData = async () => {
  try {
    // Get list of tracked stocks from the database
    const db = require('../database/db').db;
    const stocks = await db.allAsync('SELECT symbol FROM stocks');
    
    if (stocks.length === 0) {
      console.log('No stocks to update');
      return;
    }
    
    console.log(`Updating data for ${stocks.length} stocks...`);
    
    // Update each stock
    for (const stock of stocks) {
      try {
        await stockService.fetchStockData(stock.symbol);
        console.log(`Updated data for ${stock.symbol}`);
      } catch (err) {
        console.error(`Error updating data for ${stock.symbol}:`, err);
      }
      
      // Add a small delay to avoid API rate limits
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log('Stock data update completed');
  } catch (err) {
    console.error('Error in updateStockData job:', err);
  }
};

// Send daily notifications via Telegram
const sendDailyNotifications = async () => {
  try {
    // Check if Telegram notifications are enabled
    const telegramEnabled = await getSetting('telegram_enabled');
    
    if (telegramEnabled !== 'true') {
      console.log('Telegram notifications are disabled');
      return;
    }
    
    // Get pending notifications
    const db = require('../database/db').db;
    const notifications = await db.allAsync(
      'SELECT * FROM notifications WHERE is_sent = 0 ORDER BY created_at'
    );
    
    if (notifications.length === 0) {
      console.log('No pending notifications to send');
      return;
    }
    
    console.log(`Sending ${notifications.length} notifications...`);
    
    // Send each notification
    for (const notification of notifications) {
      try {
        await telegramService.sendMessage(notification.message);
        
        // Mark as sent
        await db.runAsync(
          'UPDATE notifications SET is_sent = 1, sent_at = CURRENT_TIMESTAMP WHERE id = ?',
          [notification.id]
        );
        
        console.log(`Sent notification #${notification.id}`);
      } catch (err) {
        console.error(`Error sending notification #${notification.id}:`, err);
      }
      
      // Add a small delay between messages
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    console.log('Notification sending completed');
  } catch (err) {
    console.error('Error in sendDailyNotifications job:', err);
  }
};

// Backup the database
const backupDatabase = async () => {
  try {
    const db = require('../database/db');
    const backupPath = await db.createBackup();
    console.log(`Database backup created at ${backupPath}`);
  } catch (err) {
    console.error('Error in backupDatabase job:', err);
  }
};

module.exports = {
  initScheduledJobs,
  updateStockData,
  sendDailyNotifications,
  backupDatabase
};