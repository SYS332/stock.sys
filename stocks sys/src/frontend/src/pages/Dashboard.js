import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import '../styles/Dashboard.css';

// Import components
import StockDataPanel from '../components/StockDataPanel';
import AiPredictionPanel from '../components/AiPredictionPanel';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const Dashboard = () => {
  const [stockData, setStockData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStock, setSelectedStock] = useState('AAPL');

  // Chart options
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: 'var(--text-primary)',
        },
      },
      title: {
        display: true,
        text: `${selectedStock} Stock Price`,
        color: 'var(--text-primary)',
      },
    },
    scales: {
      x: {
        grid: {
          color: 'var(--border-color)',
        },
        ticks: {
          color: 'var(--text-secondary)',
        },
      },
      y: {
        grid: {
          color: 'var(--border-color)',
        },
        ticks: {
          color: 'var(--text-secondary)',
        },
      },
    },
  };

  // Fetch stock data (using dummy data for now)
  useEffect(() => {
    setLoading(true);
    
    // Simulate API call with dummy data
    setTimeout(() => {
      const dummyData = generateDummyStockData(selectedStock);
      setStockData(dummyData);
      setLoading(false);
    }, 1000);
    
    // In a real app, you would fetch from an API like:
    // fetch(`/api/stocks/${selectedStock}`)
    //   .then(response => response.json())
    //   .then(data => {
    //     setStockData(data);
    //     setLoading(false);
    //   })
    //   .catch(err => {
    //     setError(err.message);
    //     setLoading(false);
    //   });
  }, [selectedStock]);

  // Generate dummy stock data
  const generateDummyStockData = (symbol) => {
    const dates = [];
    const prices = [];
    const volumes = [];
    
    // Generate 30 days of data
    const today = new Date();
    let basePrice = symbol === 'AAPL' ? 150 : symbol === 'MSFT' ? 300 : 100;
    
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      dates.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
      
      // Add some randomness to price
      basePrice = basePrice + (Math.random() - 0.5) * 5;
      prices.push(basePrice);
      
      // Random volume
      volumes.push(Math.floor(Math.random() * 10000000) + 1000000);
    }
    
    return {
      symbol,
      dates,
      prices,
      volumes,
      chartData: {
        labels: dates,
        datasets: [
          {
            label: `${symbol} Price`,
            data: prices,
            borderColor: '#3a506b',
            backgroundColor: 'rgba(58, 80, 107, 0.5)',
            tension: 0.1,
          },
        ],
      },
      latestPrice: prices[prices.length - 1].toFixed(2),
      change: (prices[prices.length - 1] - prices[prices.length - 2]).toFixed(2),
      changePercent: (((prices[prices.length - 1] - prices[prices.length - 2]) / prices[prices.length - 2]) * 100).toFixed(2),
    };
  };

  // Handle stock selection change
  const handleStockChange = (e) => {
    setSelectedStock(e.target.value);
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Stock Analysis Dashboard</h2>
        <div className="stock-selector">
          <label htmlFor="stock-select">Select Stock:</label>
          <select 
            id="stock-select" 
            value={selectedStock} 
            onChange={handleStockChange}
          >
            <option value="AAPL">Apple Inc. (AAPL)</option>
            <option value="MSFT">Microsoft Corp. (MSFT)</option>
            <option value="GOOGL">Alphabet Inc. (GOOGL)</option>
            <option value="AMZN">Amazon.com Inc. (AMZN)</option>
          </select>
        </div>
      </div>
      
      {loading ? (
        <div className="loading">Loading stock data...</div>
      ) : error ? (
        <div className="error">Error: {error}</div>
      ) : (
        <>
          <div className="stock-overview">
            <div className="stock-price">
              <h3>{stockData.symbol}</h3>
              <div className="price">${stockData.latestPrice}</div>
              <div className={`change ${stockData.change >= 0 ? 'positive' : 'negative'}`}>
                {stockData.change >= 0 ? '+' : ''}{stockData.change} ({stockData.changePercent}%)
              </div>
            </div>
          </div>
          
          <div className="chart-container card">
            <Line options={chartOptions} data={stockData.chartData} />
          </div>
          
          <div className="dashboard-panels">
            <StockDataPanel stockData={stockData} />
            <AiPredictionPanel stockSymbol={selectedStock} />
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;