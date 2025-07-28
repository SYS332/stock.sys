const { getDatabaseStats: getStats, createBackup: createDbBackup, initDatabase } = require('../../database/db');

// Get database statistics
const getDatabaseStats = async (req, res, next) => {
  try {
    const stats = await getStats();
    res.json(stats);
  } catch (err) {
    next(err);
  }
};

// Create a database backup
const createBackup = async (req, res, next) => {
  try {
    const backupPath = await createDbBackup();
    res.json({
      success: true,
      message: 'Database backup created successfully',
      backupPath
    });
  } catch (err) {
    next(err);
  }
};

// Initialize or reset the database
const initializeDatabase = async (req, res, next) => {
  try {
    const { reset } = req.body;
    
    if (reset) {
      // In a real app, you would want to confirm this action
      // and possibly create a backup before resetting
      
      // For now, we'll just re-initialize the database
      await initDatabase();
      
      res.json({
        success: true,
        message: 'Database reset and initialized successfully'
      });
    } else {
      // Just initialize without resetting
      await initDatabase();
      
      res.json({
        success: true,
        message: 'Database initialized successfully'
      });
    }
  } catch (err) {
    next(err);
  }
};

module.exports = {
  getDatabaseStats,
  createBackup,
  initializeDatabase
};