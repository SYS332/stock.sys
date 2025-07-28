import React, { useState, useEffect } from 'react';
import '../styles/Settings.css';

const NotificationSettings = () => {
  const [settings, setSettings] = useState({
    telegram_enabled: 'false',
    telegram_token: '',
    telegram_chat_id: '',
    notification_daily_summary: 'true',
    notification_price_alerts: 'true',
    notification_prediction_alerts: 'true',
    notification_time: '08:00'
  });
  
  const [showToken, setShowToken] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  const [testStatus, setTestStatus] = useState(null);
  
  // Fetch settings on component mount
  useEffect(() => {
    fetchSettings();
  }, []);
  
  const fetchSettings = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/settings');
      if (!response.ok) {
        throw new Error('Failed to fetch settings');
      }
      
      const data = await response.json();
      if (data.success) {
        // Update only the settings we're interested in
        const notificationSettings = {};
        for (const key in settings) {
          if (data.data[key] !== undefined) {
            notificationSettings[key] = data.data[key];
          } else {
            notificationSettings[key] = settings[key];
          }
        }
        setSettings(notificationSettings);
      } else {
        throw new Error(data.error || 'Failed to fetch settings');
      }
    } catch (err) {
      console.error('Error fetching settings:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (checked ? 'true' : 'false') : value
    }));
  };
  
  const saveSettings = async (e) => {
    e.preventDefault();
    setSaveStatus('saving');
    
    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        throw new Error(data.error || 'Failed to save settings');
      }
    } catch (err) {
      console.error('Error saving settings:', err);
      setError(err.message);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus(null), 3000);
    }
  };
  
  const testTelegramConnection = async () => {
    setTestStatus('testing');
    
    try {
      const response = await fetch('/api/notifications/test-telegram', {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.success) {
        setTestStatus('success');
        setTimeout(() => setTestStatus(null), 3000);
      } else {
        throw new Error(data.error || 'Failed to connect to Telegram');
      }
    } catch (err) {
      console.error('Error testing Telegram connection:', err);
      setError(err.message);
      setTestStatus('error');
      setTimeout(() => setTestStatus(null), 3000);
    }
  };
  
  if (loading) {
    return <div className="settings-container loading">Loading settings...</div>;
  }
  
  return (
    <div className="settings-container">
      <h1>Notification Settings</h1>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={saveSettings}>
        <div className="settings-section">
          <h2>Telegram Integration</h2>
          
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                name="telegram_enabled"
                checked={settings.telegram_enabled === 'true'}
                onChange={handleChange}
              />
              Enable Telegram Notifications
            </label>
          </div>
          
          <div className="form-group">
            <label htmlFor="telegram_token">Telegram Bot Token:</label>
            <div className="input-with-toggle">
              <input
                type={showToken ? 'text' : 'password'}
                id="telegram_token"
                name="telegram_token"
                value={settings.telegram_token}
                onChange={handleChange}
                placeholder="Enter your Telegram bot token"
                disabled={settings.telegram_enabled !== 'true'}
              />
              <button
                type="button"
                className="toggle-button"
                onClick={() => setShowToken(!showToken)}
                disabled={settings.telegram_enabled !== 'true'}
              >
                {showToken ? 'Hide' : 'Show'}
              </button>
            </div>
            <small>
              Create a bot via <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer">@BotFather</a> to get a token
            </small>
          </div>
          
          <div className="form-group">
            <label htmlFor="telegram_chat_id">Chat ID:</label>
            <input
              type="text"
              id="telegram_chat_id"
              name="telegram_chat_id"
              value={settings.telegram_chat_id}
              onChange={handleChange}
              placeholder="Enter your Telegram chat ID"
              disabled={settings.telegram_enabled !== 'true'}
            />
            <small>
              Start a chat with your bot and send a message to activate it
            </small>
          </div>
          
          <div className="test-connection">
            <button
              type="button"
              onClick={testTelegramConnection}
              disabled={settings.telegram_enabled !== 'true' || !settings.telegram_token || !settings.telegram_chat_id || testStatus === 'testing'}
              className={`test-button ${testStatus ? testStatus : ''}`}
            >
              {testStatus === 'testing' ? 'Testing...' : 
               testStatus === 'success' ? 'Test Successful!' : 
               testStatus === 'error' ? 'Test Failed!' : 
               'Test Connection'}
            </button>
          </div>
        </div>
        
        <div className="settings-section">
          <h2>Notification Preferences</h2>
          
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                name="notification_daily_summary"
                checked={settings.notification_daily_summary === 'true'}
                onChange={handleChange}
              />
              Daily Summary
            </label>
            <small>Receive a daily summary of your tracked stocks</small>
          </div>
          
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                name="notification_price_alerts"
                checked={settings.notification_price_alerts === 'true'}
                onChange={handleChange}
              />
              Price Alerts
            </label>
            <small>Receive notifications when stocks hit price targets</small>
          </div>
          
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                name="notification_prediction_alerts"
                checked={settings.notification_prediction_alerts === 'true'}
                onChange={handleChange}
              />
              Prediction Alerts
            </label>
            <small>Receive notifications for new AI predictions</small>
          </div>
          
          <div className="form-group">
            <label htmlFor="notification_time">Notification Time:</label>
            <input
              type="time"
              id="notification_time"
              name="notification_time"
              value={settings.notification_time}
              onChange={handleChange}
            />
            <small>Time for daily notifications (in your local timezone)</small>
          </div>
        </div>
        
        <div className="save-actions">
          <button
            type="submit"
            className={`save-button ${saveStatus ? saveStatus : ''}`}
            disabled={saveStatus === 'saving'}
          >
            {saveStatus === 'saving' ? 'Saving...' : 
             saveStatus === 'success' ? 'Saved Successfully!' : 
             saveStatus === 'error' ? 'Save Failed!' : 
             'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default NotificationSettings;