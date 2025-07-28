const telegramService = require('../../services/telegramService');
const { db } = require('../../database/db');

// Get all notifications
const getNotifications = async (req, res) => {
  try {
    const { limit = 50, offset = 0, sent } = req.query;
    
    let query = 'SELECT * FROM notifications';
    const params = [];
    
    // Filter by sent status if provided
    if (sent !== undefined) {
      query += ' WHERE is_sent = ?';
      params.push(sent === 'true' ? 1 : 0);
    }
    
    // Add ordering and pagination
    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    params.push(parseInt(limit), parseInt(offset));
    
    const notifications = await db.allAsync(query, params);
    
    res.json({
      success: true,
      data: notifications
    });
  } catch (err) {
    console.error('Error getting notifications:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve notifications'
    });
  }
};

// Create a new notification
const createNotification = async (req, res) => {
  try {
    const { message, type = 'general', send_now = false } = req.body;
    
    if (!message) {
      return res.status(400).json({
        success: false,
        error: 'Message is required'
      });
    }
    
    // Insert notification into database
    const result = await db.runAsync(
      'INSERT INTO notifications (message, type, is_sent, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
      [message, type, send_now ? 1 : 0]
    );
    
    const notificationId = result.lastID;
    
    // Send immediately if requested
    if (send_now) {
      try {
        await telegramService.sendMessage(message);
        
        // Update sent status
        await db.runAsync(
          'UPDATE notifications SET sent_at = CURRENT_TIMESTAMP WHERE id = ?',
          [notificationId]
        );
      } catch (sendErr) {
        console.error('Error sending notification:', sendErr);
        
        // Mark as not sent if failed
        await db.runAsync(
          'UPDATE notifications SET is_sent = 0 WHERE id = ?',
          [notificationId]
        );
        
        return res.status(200).json({
          success: true,
          data: {
            id: notificationId,
            message,
            type,
            is_sent: false,
            warning: 'Notification created but failed to send immediately'
          }
        });
      }
    }
    
    res.status(201).json({
      success: true,
      data: {
        id: notificationId,
        message,
        type,
        is_sent: send_now
      }
    });
  } catch (err) {
    console.error('Error creating notification:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to create notification'
    });
  }
};

// Send a pending notification
const sendNotification = async (req, res) => {
  try {
    const { id } = req.params;
    
    // Get the notification
    const notification = await db.getAsync(
      'SELECT * FROM notifications WHERE id = ?',
      [id]
    );
    
    if (!notification) {
      return res.status(404).json({
        success: false,
        error: 'Notification not found'
      });
    }
    
    if (notification.is_sent) {
      return res.status(400).json({
        success: false,
        error: 'Notification has already been sent'
      });
    }
    
    // Send the notification
    await telegramService.sendMessage(notification.message);
    
    // Update sent status
    await db.runAsync(
      'UPDATE notifications SET is_sent = 1, sent_at = CURRENT_TIMESTAMP WHERE id = ?',
      [id]
    );
    
    res.json({
      success: true,
      data: {
        id: parseInt(id),
        message: notification.message,
        is_sent: true,
        sent_at: new Date().toISOString()
      }
    });
  } catch (err) {
    console.error(`Error sending notification #${req.params.id}:`, err);
    res.status(500).json({
      success: false,
      error: 'Failed to send notification'
    });
  }
};

// Delete a notification
const deleteNotification = async (req, res) => {
  try {
    const { id } = req.params;
    
    // Check if notification exists
    const notification = await db.getAsync(
      'SELECT id FROM notifications WHERE id = ?',
      [id]
    );
    
    if (!notification) {
      return res.status(404).json({
        success: false,
        error: 'Notification not found'
      });
    }
    
    // Delete the notification
    await db.runAsync('DELETE FROM notifications WHERE id = ?', [id]);
    
    res.json({
      success: true,
      data: { id: parseInt(id) }
    });
  } catch (err) {
    console.error(`Error deleting notification #${req.params.id}:`, err);
    res.status(500).json({
      success: false,
      error: 'Failed to delete notification'
    });
  }
};

// Test Telegram connection
const testTelegramConnection = async (req, res) => {
  try {
    const testMessage = '🔔 *Test Notification*\n\nThis is a test message from your Stock Analysis System.\n\nTime: ' + 
      new Date().toLocaleString();
    
    await telegramService.sendMessage(testMessage);
    
    res.json({
      success: true,
      message: 'Test message sent successfully'
    });
  } catch (err) {
    console.error('Error testing Telegram connection:', err);
    res.status(500).json({
      success: false,
      error: err.message || 'Failed to send test message'
    });
  }
};

module.exports = {
  getNotifications,
  createNotification,
  sendNotification,
  deleteNotification,
  testTelegramConnection
};