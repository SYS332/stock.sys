const express = require('express');
const router = express.Router();

// Import controllers
const stockController = require('./controllers/stockController');
const settingsController = require('./controllers/settingsController');
const databaseController = require('./controllers/databaseController');
const predictionController = require('./controllers/predictionController');
const notificationController = require('./controllers/notificationController');

// Stock routes
router.get('/stocks', stockController.getAllStocks);
router.get('/stocks/:symbol', stockController.getStockBySymbol);
router.get('/stocks/:symbol/history', stockController.getStockHistory);
router.post('/stocks/refresh', stockController.refreshStockData);

// Settings routes
router.get('/settings', settingsController.getAllSettings);
router.post('/settings', settingsController.updateSettings);
router.post('/settings/test-connection', settingsController.testConnection);

// Database routes
router.get('/database/stats', databaseController.getDatabaseStats);
router.post('/database/backup', databaseController.createBackup);
router.post('/database/initialize', databaseController.initializeDatabase);

// Prediction routes
router.get('/predictions/:symbol', predictionController.getPredictions);
router.post('/predictions/generate', predictionController.generatePrediction);

// Notification routes
router.get('/notifications', notificationController.getNotifications);
router.post('/notifications', notificationController.createNotification);
router.post('/notifications/:id/send', notificationController.sendNotification);
router.delete('/notifications/:id', notificationController.deleteNotification);
router.post('/notifications/test-telegram', notificationController.testTelegramConnection);

module.exports = router;