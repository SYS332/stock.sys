import React from 'react';
import { Routes, Route } from 'react-router-dom';
import './styles/App.css';

// Pages
import Dashboard from './pages/Dashboard';
import ApiSettings from './pages/ApiSettings';
import DatabaseSettings from './pages/DatabaseSettings';
import Notifications from './pages/Notifications';
import NotificationSettings from './pages/NotificationSettings';

// Components
import Navbar from './components/Navbar';

function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/api-settings" element={<ApiSettings />} />
          <Route path="/database-settings" element={<DatabaseSettings />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/notification-settings" element={<NotificationSettings />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;