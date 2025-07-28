import React, { useState, useEffect } from 'react';
import '../styles/Settings.css';

const ApiSettings = () => {
  const [aiApiKey, setAiApiKey] = useState('');
  const [telegramToken, setTelegramToken] = useState('');
  const [stockApiKey, setStockApiKey] = useState('');
  const [stockApiProvider, setStockApiProvider] = useState('alphavantage');
  const [saveStatus, setSaveStatus] = useState(null);
  const [showAiKey, setShowAiKey] = useState(false);
  const [showTelegramToken, setShowTelegramToken] = useState(false);
  const [showStockApiKey, setShowStockApiKey] = useState(false);

  // Load saved API keys on component mount
  useEffect(() => {
    // In a real app, this would fetch from the backend
    // For now, we'll simulate loading from localStorage
    const loadedAiApiKey = localStorage.getItem('aiApiKey') || '';
    const loadedTelegramToken = localStorage.getItem('telegramToken') || '';
    const loadedStockApiKey = localStorage.getItem('stockApiKey') || '';
    const loadedStockApiProvider = localStorage.getItem('stockApiProvider') || 'alphavantage';
    
    setAiApiKey(loadedAiApiKey);
    setTelegramToken(loadedTelegramToken);
    setStockApiKey(loadedStockApiKey);
    setStockApiProvider(loadedStockApiProvider);
  }, []);

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // In a real app, this would send the data to the backend
    // For now, we'll simulate saving to localStorage
    localStorage.setItem('aiApiKey', aiApiKey);
    localStorage.setItem('telegramToken', telegramToken);
    localStorage.setItem('stockApiKey', stockApiKey);
    localStorage.setItem('stockApiProvider', stockApiProvider);
    
    // Show success message
    setSaveStatus('success');
    
    // Clear status after 3 seconds
    setTimeout(() => {
      setSaveStatus(null);
    }, 3000);
  };

  // Test connection to APIs
  const testConnection = (apiType) => {
    // In a real app, this would test the connection to the respective API
    // For now, we'll just simulate a successful connection
    alert(`${apiType} connection test successful!`);
  };

  return (
    <div className="settings-page">
      <h2>API Settings</h2>
      <p className="settings-description">
        Configure your API keys and connections for stock data, AI predictions, and notifications.
      </p>
      
      <form onSubmit={handleSubmit} className="settings-form">
        <div className="settings-section card">
          <h3>AI Prediction API</h3>
          <p>Connect to an AI service for stock predictions and analysis.</p>
          
          <div className="form-group">
            <label htmlFor="ai-api-key">AI API Key</label>
            <div className="input-with-toggle">
              <input
                type={showAiKey ? 'text' : 'password'}
                id="ai-api-key"
                value={aiApiKey}
                onChange={(e) => setAiApiKey(e.target.value)}
                placeholder="Enter your AI API key"
              />
              <button 
                type="button" 
                className="toggle-visibility" 
                onClick={() => setShowAiKey(!showAiKey)}
              >
                {showAiKey ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>
          
          <button 
            type="button" 
            className="test-button" 
            onClick={() => testConnection('AI API')}
            disabled={!aiApiKey}
          >
            Test Connection
          </button>
        </div>
        
        <div className="settings-section card">
          <h3>Telegram Notifications</h3>
          <p>Set up a Telegram bot to receive daily stock updates and alerts.</p>
          
          <div className="form-group">
            <label htmlFor="telegram-token">Telegram Bot Token</label>
            <div className="input-with-toggle">
              <input
                type={showTelegramToken ? 'text' : 'password'}
                id="telegram-token"
                value={telegramToken}
                onChange={(e) => setTelegramToken(e.target.value)}
                placeholder="Enter your Telegram bot token"
              />
              <button 
                type="button" 
                className="toggle-visibility" 
                onClick={() => setShowTelegramToken(!showTelegramToken)}
              >
                {showTelegramToken ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>
          
          <button 
            type="button" 
            className="test-button" 
            onClick={() => testConnection('Telegram Bot')}
            disabled={!telegramToken}
          >
            Test Connection
          </button>
        </div>
        
        <div className="settings-section card">
          <h3>Stock Data API</h3>
          <p>Configure the API for fetching stock market data.</p>
          
          <div className="form-group">
            <label htmlFor="stock-api-provider">API Provider</label>
            <select
              id="stock-api-provider"
              value={stockApiProvider}
              onChange={(e) => setStockApiProvider(e.target.value)}
            >
              <option value="alphavantage">Alpha Vantage</option>
              <option value="twelvedata">Twelve Data</option>
              <option value="yahoofinance">Yahoo Finance</option>
            </select>
          </div>
          
          <div className="form-group">
            <label htmlFor="stock-api-key">API Key</label>
            <div className="input-with-toggle">
              <input
                type={showStockApiKey ? 'text' : 'password'}
                id="stock-api-key"
                value={stockApiKey}
                onChange={(e) => setStockApiKey(e.target.value)}
                placeholder="Enter your stock API key"
              />
              <button 
                type="button" 
                className="toggle-visibility" 
                onClick={() => setShowStockApiKey(!showStockApiKey)}
              >
                {showStockApiKey ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>
          
          <button 
            type="button" 
            className="test-button" 
            onClick={() => testConnection('Stock API')}
            disabled={!stockApiKey}
          >
            Test Connection
          </button>
        </div>
        
        <div className="form-actions">
          <button type="submit" className="save-button">Save All Settings</button>
          
          {saveStatus === 'success' && (
            <div className="save-status success">Settings saved successfully!</div>
          )}
          
          {saveStatus === 'error' && (
            <div className="save-status error">Error saving settings. Please try again.</div>
          )}
        </div>
      </form>
    </div>
  );
};

export default ApiSettings;