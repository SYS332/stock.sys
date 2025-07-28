# Stock Analysis Application

A comprehensive stock analysis application with AI-powered predictions, real-time data fetching, and Telegram notifications. Built with React frontend and FastAPI backend.

## 🚀 Features

### 📊 Core Functionality
- **Real-time Stock Data**: Integration with multiple APIs (Alpha Vantage, Twelve Data, Yahoo Finance)
- **AI-Powered Predictions**: Support for OpenAI GPT, Claude, and custom models
- **Technical Analysis**: RSI, MACD, Moving Averages, Bollinger Bands
- **Historical Data**: Comprehensive price history and trend analysis
- **Portfolio Tracking**: Monitor multiple stocks simultaneously

### 🤖 AI & Automation
- **Flexible AI Integration**: OpenAI, Claude, or custom model support
- **Automated Predictions**: Scheduled AI analysis for all tracked stocks
- **Prediction Accuracy Tracking**: Evaluate and improve prediction models
- **Smart Alerts**: AI-driven price movement notifications

### 📱 Notifications & Alerts
- **Telegram Bot Integration**: Daily summaries and real-time alerts
- **Customizable Notifications**: Configure alert thresholds and timing
- **Multi-channel Support**: Email and webhook notifications (extensible)

### 🔒 Security & Configuration
- **Encrypted API Keys**: AES-256 encryption for sensitive data
- **Secure Storage**: Encrypted database storage for all credentials
- **Environment-based Configuration**: Development, staging, and production configs
- **Rate Limiting**: Built-in API rate limiting and quota management

### 📈 Analytics & Reporting
- **Performance Metrics**: Track prediction accuracy and model performance
- **Historical Analysis**: Comprehensive backtesting capabilities
- **Export Functionality**: CSV/Excel export for further analysis
- **Custom Dashboards**: Configurable views and metrics

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │   External APIs │
│                 │    │                 │    │                 │
│ • Dashboard     │◄──►│ • REST API      │◄──►│ • Stock Data    │
│ • Settings      │    │ • WebSocket     │    │ • AI Services   │
│ • Charts        │    │ • Scheduler     │    │ • Telegram      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   SQLite DB     │
                       │                 │
                       │ • Stock Data    │
                       │ • Predictions   │
                       │ • User Settings │
                       └─────────────────┘
```

## 🛠️ Technology Stack

### Frontend
- **React 18** - Modern React with hooks and context
- **Chart.js** - Interactive stock charts and visualizations
- **TailwindCSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM with async support
- **APScheduler** - Background job scheduling
- **Cryptography** - AES-256 encryption for sensitive data
- **Pydantic** - Data validation and serialization
- **Uvicorn** - ASGI server for production

### Database
- **SQLite** - Default lightweight database
- **PostgreSQL** - Optional for production scaling
- **Redis** - Optional caching layer

### External Integrations
- **Stock APIs**: Alpha Vantage, Twelve Data, Yahoo Finance
- **AI Services**: OpenAI GPT, Anthropic Claude, Custom models
- **Notifications**: Telegram Bot API
- **Deployment**: Docker, Docker Compose

## 🚀 Quick Start

### Prerequisites
- **Node.js** 18+ and npm
- **Python** 3.11+
- **Docker** (optional, recommended)

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stock-analysis-app
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs

### Option 2: Manual Setup

#### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd src/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   python -c "from database.models import init_db; import asyncio; asyncio.run(init_db())"
   ```

6. **Run the backend**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd src/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm start
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Application Settings
ENVIRONMENT=development
SECRET_KEY=your-secret-key-change-in-production
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./data/stocks.db

# Encryption
ENCRYPTION_PASSWORD=your-encryption-password
ENCRYPTION_SALT=your-encryption-salt

# API Keys (will be encrypted and stored in database)
STOCK_API_KEY=your-stock-api-key
STOCK_API_PROVIDER=alphavantage
AI_API_KEY=your-ai-api-key
AI_API_PROVIDER=openai
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Scheduling
DATA_FETCH_INTERVAL_HOURS=1
PREDICTION_INTERVAL_HOURS=6
TELEGRAM_NOTIFICATION_HOUR=9

# Optional: PostgreSQL (for production)
POSTGRES_DB=stockanalysis
POSTGRES_USER=stockuser
POSTGRES_PASSWORD=stockpass

# Optional: Redis (for caching)
REDIS_URL=redis://localhost:6379
```

### API Provider Setup

#### Stock Data APIs

1. **Alpha Vantage** (Recommended for beginners)
   - Sign up at https://www.alphavantage.co/
   - Free tier: 5 calls/minute, 500 calls/day
   - Get your API key and add to settings

2. **Twelve Data** (Best for production)
   - Sign up at https://twelvedata.com/
   - Free tier: 8 calls/minute, 800 calls/day
   - More reliable and comprehensive data

3. **Yahoo Finance** (Free, no API key required)
   - No registration needed
   - Unofficial API, use with caution
   - Good for development and testing

#### AI Services

1. **OpenAI GPT** (Recommended)
   - Sign up at https://platform.openai.com/
   - Get API key from dashboard
   - Pay-per-use pricing

2. **Anthropic Claude**
   - Sign up at https://console.anthropic.com/
   - Get API key from dashboard
   - Alternative to OpenAI

3. **Custom Models**
   - Configure your own model endpoint
   - Supports OpenAI-compatible APIs

#### Telegram Bot

1. **Create a Telegram Bot**
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Get your bot token

2. **Get Chat ID**
   - Start a conversation with your bot
   - Send a message
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your chat ID in the response

## 📊 Usage Guide

### Initial Setup

1. **Access the Application**
   - Open http://localhost:8000 in your browser

2. **Configure API Keys**
   - Go to "API Settings" page
   - Add your stock data API key
   - Add AI service API key (optional)
   - Add Telegram bot token (optional)
   - Test connections to verify setup

3. **Database Setup**
   - Go to "Database Settings" page
   - Initialize the database
   - Verify connection status

### Adding Stocks

1. **Search and Add Stocks**
   - Use the search functionality to find stocks
   - Add stocks to your watchlist
   - Configure alert thresholds

2. **Fetch Initial Data**
   - Use the "Refresh All" button to fetch initial data
   - Wait for data to populate

### AI Predictions

1. **Generate Predictions**
   - Go to individual stock pages
   - Click "Generate Prediction"
   - Choose timeframe (short/medium/long term)
   - Review AI analysis and reasoning

2. **Monitor Accuracy**
   - Check prediction accuracy over time
   - Use insights to improve model selection

### Notifications

1. **Configure Telegram**
   - Add your bot token in API settings
   - Set notification preferences
   - Test with sample alerts

2. **Customize Alerts**
   - Set price change thresholds
   - Configure notification timing
   - Enable/disable specific alert types

## 🔧 Development

### Project Structure

```
stock-analysis-app/
├── src/
│   ├── frontend/                 # React frontend
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── components/       # Reusable components
│   │   │   ├── pages/           # Page components
│   │   │   ├── styles/          # CSS files
│   │   │   └── utils/           # Utility functions
│   │   └── package.json
│   └── backend/                 # FastAPI backend
│       ├── api/
│       │   └── routes/          # API route handlers
│       ├── database/
│       │   └── models.py        # Database models
│       ├── services/            # Business logic services
│       ├── config.py            # Configuration
│       ├── main.py              # Application entry point
│       └── requirements.txt
├── docker-compose.yml           # Docker configuration
├── Dockerfile                   # Docker build instructions
└── README.md                    # This file
```

### Adding New Features

1. **Backend API Endpoints**
   - Add new routes in `src/backend/api/routes/`
   - Update database models if needed
   - Add business logic in `src/backend/services/`

2. **Frontend Components**
   - Create components in `src/frontend/src/components/`
   - Add pages in `src/frontend/src/pages/`
   - Update routing in `App.js`

3. **Database Changes**
   - Update models in `database/models.py`
   - Create migration scripts
   - Test with sample data

### Testing

```bash
# Backend tests
cd src/backend
pytest

# Frontend tests
cd src/frontend
npm test

# Integration tests
docker-compose -f docker-compose.test.yml up
```

### Code Quality

```bash
# Python formatting and linting
black src/backend/
flake8 src/backend/
mypy src/backend/

# JavaScript/React linting
cd src/frontend
npm run lint
npm run format
```

## 🚀 Deployment

### Production Deployment

1. **Prepare Environment**
   ```bash
   # Set production environment variables
   export ENVIRONMENT=production
   export DEBUG=false
   export SECRET_KEY=your-production-secret-key
   ```

2. **Build and Deploy**
   ```bash
   # Build production images
   docker-compose -f docker-compose.prod.yml build

   # Deploy
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Configure Reverse Proxy**
   - Use Nginx for SSL termination
   - Configure domain and certificates
   - Set up monitoring and logging

### Scaling Considerations

- **Database**: Migrate to PostgreSQL for better performance
- **Caching**: Add Redis for API response caching
- **Load Balancing**: Use multiple backend instances
- **Monitoring**: Add Prometheus/Grafana for metrics
- **Logging**: Centralized logging with ELK stack

## 🔍 Troubleshooting

### Common Issues

1. **API Rate Limits**
   - Check your API provider limits
   - Adjust fetch intervals in configuration
   - Consider upgrading to paid tiers

2. **Database Connection Issues**
   - Verify database file permissions
   - Check SQLite file path
   - Ensure data directory exists

3. **Telegram Bot Not Working**
   - Verify bot token is correct
   - Check chat ID configuration
   - Test bot connection in settings

4. **AI Predictions Failing**
   - Verify AI API key is valid
   - Check API quota and billing
   - Review error logs for details

### Logs and Debugging

```bash
# View application logs
docker-compose logs -f stock-analysis-app

# Backend logs
tail -f logs/app.log

# Database queries (development)
export LOG_LEVEL=DEBUG
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests for new functionality**
5. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
6. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 for Python code
- Use ESLint/Prettier for JavaScript
- Write tests for new features
- Update documentation
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **React** - Frontend library
- **Chart.js** - Charting library
- **Alpha Vantage** - Stock data API
- **OpenAI** - AI services
- **Telegram** - Bot API for notifications

## 📞 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Email**: [your-email@example.com]

---

**Built with ❤️ for the trading community**