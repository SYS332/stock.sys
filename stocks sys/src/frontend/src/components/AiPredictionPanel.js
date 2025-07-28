import React, { useState } from 'react';
import '../styles/DataPanel.css';

const AiPredictionPanel = ({ stockSymbol }) => {
  const [aiConnected, setAiConnected] = useState(false);
  const [predictions, setPredictions] = useState(null);

  // Dummy predictions - in a real app, these would come from the AI API
  const dummyPredictions = {
    shortTerm: {
      prediction: 'Bullish',
      confidence: '75%',
      targetPrice: `$${(Math.random() * 20 + 150).toFixed(2)}`,
      timeframe: '7 days',
    },
    mediumTerm: {
      prediction: 'Neutral',
      confidence: '60%',
      targetPrice: `$${(Math.random() * 30 + 160).toFixed(2)}`,
      timeframe: '30 days',
    },
    longTerm: {
      prediction: 'Bullish',
      confidence: '80%',
      targetPrice: `$${(Math.random() * 50 + 170).toFixed(2)}`,
      timeframe: '90 days',
    },
    signals: [
      { name: 'RSI', value: (Math.random() * 100).toFixed(2), interpretation: 'Neutral' },
      { name: 'MACD', value: 'Positive', interpretation: 'Bullish' },
      { name: 'Moving Averages', value: 'Above 200-day MA', interpretation: 'Bullish' },
    ],
  };

  // Simulate connecting to AI API
  const handleConnectAi = () => {
    // In a real app, this would check if the API key is valid
    setAiConnected(true);
    setPredictions(dummyPredictions);
  };

  return (
    <div className="data-panel card">
      <div className="data-panel-header">
        <h3>AI Predictions</h3>
        <div className="connection-status">
          <span className={`status-indicator ${aiConnected ? 'status-connected' : 'status-disconnected'}`}></span>
          <span>{aiConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      {!aiConnected ? (
        <div className="ai-connect-prompt">
          <p>Connect to the AI prediction service to get stock insights and predictions.</p>
          <button onClick={handleConnectAi}>Connect AI Service</button>
          <p className="note">Note: You need to set up your AI API key in the API Settings page.</p>
        </div>
      ) : (
        <div className="prediction-content">
          <div className="prediction-timeframes">
            <div className="timeframe">
              <h4>Short Term ({predictions.shortTerm.timeframe})</h4>
              <div className={`prediction ${predictions.shortTerm.prediction.toLowerCase()}`}>
                {predictions.shortTerm.prediction}
              </div>
              <div className="prediction-details">
                <div>Confidence: {predictions.shortTerm.confidence}</div>
                <div>Target: {predictions.shortTerm.targetPrice}</div>
              </div>
            </div>
            
            <div className="timeframe">
              <h4>Medium Term ({predictions.mediumTerm.timeframe})</h4>
              <div className={`prediction ${predictions.mediumTerm.prediction.toLowerCase()}`}>
                {predictions.mediumTerm.prediction}
              </div>
              <div className="prediction-details">
                <div>Confidence: {predictions.mediumTerm.confidence}</div>
                <div>Target: {predictions.mediumTerm.targetPrice}</div>
              </div>
            </div>
            
            <div className="timeframe">
              <h4>Long Term ({predictions.longTerm.timeframe})</h4>
              <div className={`prediction ${predictions.longTerm.prediction.toLowerCase()}`}>
                {predictions.longTerm.prediction}
              </div>
              <div className="prediction-details">
                <div>Confidence: {predictions.longTerm.confidence}</div>
                <div>Target: {predictions.longTerm.targetPrice}</div>
              </div>
            </div>
          </div>
          
          <div className="technical-signals">
            <h4>Technical Signals</h4>
            <table className="signals-table">
              <thead>
                <tr>
                  <th>Indicator</th>
                  <th>Value</th>
                  <th>Signal</th>
                </tr>
              </thead>
              <tbody>
                {predictions.signals.map((signal, index) => (
                  <tr key={index}>
                    <td>{signal.name}</td>
                    <td>{signal.value}</td>
                    <td className={signal.interpretation.toLowerCase()}>{signal.interpretation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default AiPredictionPanel;