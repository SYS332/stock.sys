const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');
const { promisify } = require('util');

// Get database path from environment or use default
const dbPath = process.env.DB_PATH || path.join(__dirname, '../..', 'stockdata.db');

// Ensure the directory exists
const dbDir = path.dirname(dbPath);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

// Create database connection
let db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Error connecting to the database:', err.message);
  } else {
    console.log('Connected to the SQLite database at', dbPath);
  }
});

// Promisify database methods
db.runAsync = promisify(db.run.bind(db));
db.getAsync = promisify(db.get.bind(db));
db.allAsync = promisify(db.all.bind(db));
db.execAsync = promisify(db.exec.bind(db));

// Initialize database schema
const initDatabase = async () => {
  try {
    // Create settings table
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Create stocks table
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS stocks (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        exchange TEXT,
        sector TEXT,
        industry TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Create historical_prices table
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS historical_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (symbol) REFERENCES stocks(symbol),
        UNIQUE(symbol, date)
      )
    `);
    
    // Create predictions table
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        prediction_type TEXT,
        timeframe TEXT,
        prediction TEXT,
        confidence REAL,
        target_price REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (symbol) REFERENCES stocks(symbol)
      )
    `);
    
    // Create notifications table
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        symbol TEXT,
        message TEXT,
        is_sent BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sent_at TIMESTAMP,
        FOREIGN KEY (symbol) REFERENCES stocks(symbol)
      )
    `);
    
    // Insert default settings if they don't exist
    const defaultSettings = [
      { key: 'stock_api_provider', value: 'alphavantage' },
      { key: 'data_retention_days', value: '365' },
      { key: 'auto_backup', value: 'weekly' },
    ];
    
    for (const setting of defaultSettings) {
      await db.runAsync(
        'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
        [setting.key, setting.value]
      );
    }
    
    console.log('Database schema initialized successfully');
    return true;
  } catch (err) {
    console.error('Error initializing database schema:', err);
    throw err;
  }
};

// Get a setting from the database
const getSetting = async (key) => {
  try {
    const result = await db.getAsync('SELECT value FROM settings WHERE key = ?', [key]);
    return result ? result.value : null;
  } catch (err) {
    console.error(`Error getting setting ${key}:`, err);
    throw err;
  }
};

// Update a setting in the database
const updateSetting = async (key, value) => {
  try {
    await db.runAsync(
      'INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
      [key, value]
    );
    return true;
  } catch (err) {
    console.error(`Error updating setting ${key}:`, err);
    throw err;
  }
};

// Get database statistics
const getDatabaseStats = async () => {
  try {
    const stats = {};
    
    // Get table counts
    const tables = ['stocks', 'historical_prices', 'predictions', 'notifications'];
    for (const table of tables) {
      const result = await db.getAsync(`SELECT COUNT(*) as count FROM ${table}`);
      stats[table] = result.count;
    }
    
    // Get database size
    const dbSizeInBytes = fs.statSync(dbPath).size;
    stats.size = (dbSizeInBytes / (1024 * 1024)).toFixed(2) + ' MB';
    
    // Get last backup time from settings
    const lastBackup = await getSetting('last_backup_time');
    stats.lastBackup = lastBackup || 'Never';
    
    return stats;
  } catch (err) {
    console.error('Error getting database stats:', err);
    throw err;
  }
};

// Create a database backup
const createBackup = async () => {
  try {
    const backupDir = path.join(dbDir, 'backups');
    if (!fs.existsSync(backupDir)) {
      fs.mkdirSync(backupDir, { recursive: true });
    }
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = path.join(backupDir, `stockdata-backup-${timestamp}.db`);
    
    // Create a read stream from the database file
    const source = fs.createReadStream(dbPath);
    const destination = fs.createWriteStream(backupPath);
    
    // Return a promise that resolves when the copy is complete
    return new Promise((resolve, reject) => {
      source.pipe(destination);
      destination.on('finish', async () => {
        // Update the last backup time in settings
        await updateSetting('last_backup_time', new Date().toISOString());
        resolve(backupPath);
      });
      destination.on('error', reject);
    });
  } catch (err) {
    console.error('Error creating database backup:', err);
    throw err;
  }
};

// Close the database connection
const closeDatabase = () => {
  return new Promise((resolve, reject) => {
    db.close((err) => {
      if (err) {
        console.error('Error closing database:', err.message);
        reject(err);
      } else {
        console.log('Database connection closed');
        resolve();
      }
    });
  });
};

module.exports = {
  db,
  initDatabase,
  getSetting,
  updateSetting,
  getDatabaseStats,
  createBackup,
  closeDatabase
};