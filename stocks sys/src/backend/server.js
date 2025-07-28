const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

// Import routes
const apiRoutes = require('./api/routes');

// Import services
const { initScheduledJobs } = require('./services/scheduler');
const { initDatabase } = require('./database/db');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize database
initDatabase()
  .then(() => {
    console.log('Database initialized successfully');
    
    // Start scheduled jobs (data fetching, notifications, etc.)
    initScheduledJobs();
  })
  .catch(err => {
    console.error('Database initialization failed:', err);
    process.exit(1);
  });

// API routes
app.use('/api', apiRoutes);

// Serve static files from the React app in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../../frontend/build')));
  
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../../frontend/build', 'index.html'));
  });
}

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'An unexpected error occurred'
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});