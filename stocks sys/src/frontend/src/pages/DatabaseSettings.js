import React, { useState, useEffect } from 'react';
import '../styles/Settings.css';

const DatabaseSettings = () => {
  const [dbPath, setDbPath] = useState('');
  const [dbStatus, setDbStatus] = useState('disconnected');
  const [saveStatus, setSaveStatus] = useState(null);
  const [dbStats, setDbStats] = useState(null);
  const [isInitializing, setIsInitializing] = useState(false);

  // Load database settings on component mount
  useEffect(() => {
    // In a real app, this would fetch from the backend
    const loadedDbPath = localStorage.getItem('dbPath') || './data/stocks.db';
    setDbPath(loadedDbPath);
    
    // Simulate checking database status
    checkDatabaseStatus();
  }, []);

  // Check database connection status
  const checkDatabaseStatus = async () => {
    try {
      // In a real app, this would ping the backend to check DB status
      // For now, simulate a connection check
      setTimeout(() => {
        const isConnected = localStorage.getItem('dbInitialized') === 'true';
        setDbStatus(isConnected ? 'connected' : 'disconnected');
        
        if (isConnected) {
          // Simulate database statistics
          setDbStats({
            totalStocks: Math.floor(Math.random() * 100) + 50,
            totalPriceRecords: Math.floor(Math.random() * 10000) + 5000,
            totalPredictions: Math.floor(Math.random() * 500) + 100,
            lastUpdate: new Date().toLocaleString(),
            dbSize: '2.4 MB'
          });
        }
      }, 1000);
    } catch (error) {
      setDbStatus('error');
    }
  };

  // Initialize database
  const initializeDatabase = async () => {
    setIsInitializing(true);
    
    try {
      // In a real app, this would call the backend to initialize the database
      // For now, simulate the initialization process
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      localStorage.setItem('dbInitialized', 'true');
      localStorage.setItem('dbPath', dbPath);
      
      setDbStatus('connected');
      setSaveStatus('success');
      checkDatabaseStatus();
      
    } catch (error) {
      setSaveStatus('error');
      setDbStatus('error');
    } finally {
      setIsInitializing(false);
    }
  };

  // Reset database
  const resetDatabase = async () => {
    if (!window.confirm('Are you sure you want to reset the database? This will delete all stored data.')) {
      return;
    }
    
    try {
      // In a real app, this would call the backend to reset the database
      localStorage.removeItem('dbInitialized');
      setDbStatus('disconnected');
      setDbStats(null);
      setSaveStatus('reset');
    } catch (error) {
      setSaveStatus('error');
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    localStorage.setItem('dbPath', dbPath);
    setSaveStatus('pathSaved');
    
    setTimeout(() => {
      setSaveStatus(null);
    }, 3000);
  };

  return (
    <div className="settings-page">
      <h2>Database Settings</h2>
      <p className="settings-description">
        Configure your local SQLite database for storing stock data, predictions, and application settings.
      </p>
      
      <div className="settings-section card">
        <h3>Database Status</h3>
        <div className="db-status">
          <div className="status-row">
            <span>Connection Status:</span>
            <div className="status-indicator-wrapper">
              <span className={`status-indicator ${
                dbStatus === 'connected' ? 'status-connected' : 
                dbStatus === 'error' ? 'status-error' : 'status-disconnected'
              }`}></span>
              <span className={`status-text ${dbStatus}`}>
                {dbStatus === 'connected' ? 'Connected' : 
                 dbStatus === 'error' ? 'Error' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
        
        {dbStats && (
          <div className="db-stats">
            <h4>Database Statistics</h4>
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-label">Total Stocks</div>
                <div className="stat-value">{dbStats.totalStocks}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Price Records</div>
                <div className="stat-value">{dbStats.totalPriceRecords.toLocaleString()}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">AI Predictions</div>
                <div className="stat-value">{dbStats.totalPredictions}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Database Size</div>
                <div className="stat-value">{dbStats.dbSize}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Last Update</div>
                <div className="stat-value">{dbStats.lastUpdate}</div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <form onSubmit={handleSubmit} className="settings-form">
        <div className="settings-section card">
          <h3>Database Configuration</h3>
          
          <div className="form-group">
            <label htmlFor="db-path">Database Path</label>
            <input
              type="text"
              id="db-path"
              value={dbPath}
              onChange={(e) => setDbPath(e.target.value)}
              placeholder="Enter database file path"
            />
            <small className="form-help">
              Specify the path where the SQLite database file should be stored.
            </small>
          </div>
          
          <div className="form-actions">
            <button type="submit" className="save-button">
              Save Path
            </button>
            
            <button 
              type="button" 
              className="init-button"
              onClick={initializeDatabase}
              disabled={isInitializing || dbStatus === 'connected'}
            >
              {isInitializing ? 'Initializing...' : 'Initialize Database'}
            </button>
            
            <button 
              type="button" 
              className="reset-button"
              onClick={resetDatabase}
              disabled={dbStatus !== 'connected'}
            >
              Reset Database
            </button>
          </div>
          
          {saveStatus === 'success' && (
            <div className="save-status success">Database initialized successfully!</div>
          )}
          
          {saveStatus === 'pathSaved' && (
            <div className="save-status success">Database path saved!</div>
          )}
          
          {saveStatus === 'reset' && (
            <div className="save-status warning">Database has been reset.</div>
          )}
          
          {saveStatus === 'error' && (
            <div className="save-status error">Error with database operation. Please try again.</div>
          )}
        </div>
      </form>
      
      <div className="settings-section card">
        <h3>Database Actions</h3>
        <p>Manage your database with these utility actions.</p>
        
        <div className="action-buttons">
          <button 
            className="action-button"
            onClick={checkDatabaseStatus}
          >
            Refresh Status
          </button>
          
          <button 
            className="action-button"
            disabled={dbStatus !== 'connected'}
          >
            Export Data
          </button>
          
          <button 
            className="action-button"
            disabled={dbStatus !== 'connected'}
          >
            Import Data
          </button>
          
          <button 
            className="action-button"
            disabled={dbStatus !== 'connected'}
          >
            Backup Database
          </button>
        </div>
      </div>
    </div>
  );
};

export default DatabaseSettings;