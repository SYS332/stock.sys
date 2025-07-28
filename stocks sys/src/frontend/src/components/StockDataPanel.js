import React from 'react';
import '../styles/DataPanel.css';

const StockDataPanel = ({ stockData }) => {
  if (!stockData) return null;

  // Generate some dummy metrics for display
  const metrics = [
    { name: 'Open', value: `$${(stockData.prices[0]).toFixed(2)}` },
    { name: 'High', value: `$${Math.max(...stockData.prices).toFixed(2)}` },
    { name: 'Low', value: `$${Math.min(...stockData.prices).toFixed(2)}` },
    { name: 'Volume', value: stockData.volumes[stockData.volumes.length - 1].toLocaleString() },
    { name: '52-Week High', value: `$${(Math.max(...stockData.prices) + 10).toFixed(2)}` },
    { name: '52-Week Low', value: `$${(Math.min(...stockData.prices) - 10).toFixed(2)}` },
    { name: 'Market Cap', value: `$${(stockData.prices[stockData.prices.length - 1] * 1000000000 / 1000000000).toFixed(2)}B` },
    { name: 'P/E Ratio', value: (Math.random() * 30 + 10).toFixed(2) },
  ];

  return (
    <div className="data-panel card">
      <div className="data-panel-header">
        <h3>Daily Stock Data</h3>
        <span className="last-updated">Last updated: {new Date().toLocaleString()}</span>
      </div>
      <div className="data-grid">
        {metrics.map((metric, index) => (
          <div key={index} className="data-item">
            <div className="data-label">{metric.name}</div>
            <div className="data-value">{metric.value}</div>
          </div>
        ))}
      </div>
      <div className="data-footer">
        <button className="refresh-button">Refresh Data</button>
      </div>
    </div>
  );
};

export default StockDataPanel;