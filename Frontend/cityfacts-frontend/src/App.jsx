// src/App.js
import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [cityName, setCityName] = useState('');
  const [cityFacts, setCityFacts] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!cityName.trim()) {
      setError('Please enter a city name');
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      // First check if city exists in our database
      const response = await axios.get(`http://localhost:8000/city/${cityName}`);
      
      if (response.data.facts) {
        // City found in database
        setCityFacts(response.data.facts);
      } else {
        // City not in database, fetch from Gemini API
        const geminiResponse = await axios.get(`http://localhost:8000/city/gemini/${cityName}`);
        setCityFacts(geminiResponse.data.facts);
        
        // Save the facts to our database
        await axios.post('http://localhost:8000/city', {
          name: cityName,
          facts: geminiResponse.data.facts
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch city facts');
      } finally {
        setIsLoading(false);
      }
  };

  return (
    <div className="app-container" >
      <div className="content-wrapper">
        <h1 className="app-title">City Facts Explorer</h1>
        <p className="app-subtitle">Discover interesting facts about cities around the world</p>
        
        <form onSubmit={handleSubmit} className="search-form">
          <div className="input-group">
            <input
              type="text"
              value={cityName}
              onChange={(e) => setCityName(e.target.value)}
              placeholder="Enter a city name (e.g., Paris, Tokyo)"
              className="search-input"
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading} className="search-button">
              {isLoading ? (
                <>
                  <span className="spinner"></span>
                  Searching...
                </>
              ) : (
                'Get City Facts'
              )}
            </button>
          </div>
        </form>
        
        {error && <div className="error-message">{error}</div>}
        
        <div className="facts-container">
          <h2 className="facts-title">
            {cityFacts ? `About ${cityName}` : 'City Facts Will Appear Here'}
          </h2>
          <div className="facts-textarea">
            {cityFacts ? (
              cityFacts.split('\n').map((line, i) => (
                <p key={i} className="fact-line">{line}</p>
              ))
            ) : (
              <p className="placeholder-text">
                Enter a city name above to discover interesting facts about its history, culture, and more.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;