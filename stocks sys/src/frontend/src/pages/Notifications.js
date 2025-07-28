import React, { useState, useEffect } from 'react';
import '../styles/Notifications.css';

const Notifications = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [messageType, setMessageType] = useState('general');
  const [sendNow, setSendNow] = useState(false);
  const [filter, setFilter] = useState('all'); // all, sent, pending

  // Fetch notifications from the API
  const fetchNotifications = async () => {
    setLoading(true);
    try {
      // Build query parameters based on filter
      let queryParams = '';
      if (filter === 'sent') {
        queryParams = '?sent=true';
      } else if (filter === 'pending') {
        queryParams = '?sent=false';
      }

      const response = await fetch(`/api/notifications${queryParams}`);
      if (!response.ok) {
        throw new Error('Failed to fetch notifications');
      }
      
      const data = await response.json();
      if (data.success) {
        setNotifications(data.data);
      } else {
        throw new Error(data.error || 'Failed to fetch notifications');
      }
    } catch (err) {
      console.error('Error fetching notifications:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Load notifications on component mount and when filter changes
  useEffect(() => {
    fetchNotifications();
  }, [filter]);

  // Create a new notification
  const createNotification = async (e) => {
    e.preventDefault();
    
    if (!newMessage.trim()) {
      setError('Message cannot be empty');
      return;
    }
    
    try {
      const response = await fetch('/api/notifications', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: newMessage,
          type: messageType,
          send_now: sendNow
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Clear form and refresh notifications
        setNewMessage('');
        setSendNow(false);
        setError(null);
        fetchNotifications();
      } else {
        throw new Error(data.error || 'Failed to create notification');
      }
    } catch (err) {
      console.error('Error creating notification:', err);
      setError(err.message);
    }
  };

  // Send a pending notification
  const sendNotification = async (id) => {
    try {
      const response = await fetch(`/api/notifications/${id}/send`, {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Refresh notifications
        fetchNotifications();
      } else {
        throw new Error(data.error || 'Failed to send notification');
      }
    } catch (err) {
      console.error(`Error sending notification #${id}:`, err);
      setError(err.message);
    }
  };

  // Delete a notification
  const deleteNotification = async (id) => {
    if (!window.confirm('Are you sure you want to delete this notification?')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/notifications/${id}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Refresh notifications
        fetchNotifications();
      } else {
        throw new Error(data.error || 'Failed to delete notification');
      }
    } catch (err) {
      console.error(`Error deleting notification #${id}:`, err);
      setError(err.message);
    }
  };

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="notifications-container">
      <h1>Notifications</h1>
      
      {/* Create new notification form */}
      <div className="notification-form-container">
        <h2>Create New Notification</h2>
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={createNotification} className="notification-form">
          <div className="form-group">
            <label htmlFor="messageType">Type:</label>
            <select 
              id="messageType" 
              value={messageType} 
              onChange={(e) => setMessageType(e.target.value)}
            >
              <option value="general">General</option>
              <option value="alert">Alert</option>
              <option value="update">Update</option>
            </select>
          </div>
          
          <div className="form-group">
            <label htmlFor="message">Message:</label>
            <textarea 
              id="message" 
              value={newMessage} 
              onChange={(e) => setNewMessage(e.target.value)} 
              placeholder="Enter notification message..."
              rows="4"
              required
            />
            <small>You can use Markdown formatting in your message.</small>
          </div>
          
          <div className="form-group checkbox-group">
            <label>
              <input 
                type="checkbox" 
                checked={sendNow} 
                onChange={(e) => setSendNow(e.target.checked)} 
              />
              Send immediately
            </label>
          </div>
          
          <button type="submit" className="create-button">
            Create Notification
          </button>
        </form>
      </div>
      
      {/* Notifications list */}
      <div className="notifications-list-container">
        <div className="notifications-header">
          <h2>Notification History</h2>
          <div className="filter-controls">
            <label htmlFor="filter">Filter:</label>
            <select 
              id="filter" 
              value={filter} 
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="all">All</option>
              <option value="sent">Sent</option>
              <option value="pending">Pending</option>
            </select>
            <button onClick={fetchNotifications} className="refresh-button">
              Refresh
            </button>
          </div>
        </div>
        
        {loading ? (
          <div className="loading">Loading notifications...</div>
        ) : notifications.length === 0 ? (
          <div className="no-notifications">No notifications found</div>
        ) : (
          <div className="notifications-list">
            {notifications.map((notification) => (
              <div 
                key={notification.id} 
                className={`notification-item ${notification.is_sent ? 'sent' : 'pending'}`}
              >
                <div className="notification-header">
                  <span className="notification-type">{notification.type}</span>
                  <span className="notification-status">
                    {notification.is_sent ? 'Sent' : 'Pending'}
                  </span>
                </div>
                
                <div className="notification-message">{notification.message}</div>
                
                <div className="notification-meta">
                  <div>
                    <strong>Created:</strong> {formatDate(notification.created_at)}
                  </div>
                  {notification.is_sent && (
                    <div>
                      <strong>Sent:</strong> {formatDate(notification.sent_at)}
                    </div>
                  )}
                </div>
                
                <div className="notification-actions">
                  {!notification.is_sent && (
                    <button 
                      onClick={() => sendNotification(notification.id)}
                      className="send-button"
                    >
                      Send Now
                    </button>
                  )}
                  <button 
                    onClick={() => deleteNotification(notification.id)}
                    className="delete-button"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Notifications;