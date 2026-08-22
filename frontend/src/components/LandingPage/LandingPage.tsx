import React from 'react';
import './LandingPage.css';

interface LandingPageProps {
  onStartConversation: (initialMessage?: string) => void;
  onManageBooking: () => void;
}

const POPULAR_SEARCHES = [
  "2BHK in Koramangala under 40k",
  "Room in a flat near Whitefield",
  "Budget under 30k",
  "Pet-friendly flat in HSR Layout",
  "3BHK for family in Indiranagar",
  "Near Metro Station",
];

export const LandingPage: React.FC<LandingPageProps> = ({ 
  onStartConversation, 
  onManageBooking 
}) => {
  const [inputValue, setInputValue] = React.useState('');

  const handleSend = () => {
    if (inputValue.trim()) {
      onStartConversation(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <div className="landing">
      {/* Hero Section */}
      <div className="landing-hero animate-fade-in-up">
        <div className="landing-hero-badge">
          <span>✨</span> AI-Powered Voice Assistant
        </div>
        <h1 className="landing-title">
          Find Your Perfect Rental in{' '}
          <span className="text-gradient">Bengaluru</span>
        </h1>
        <p className="landing-subtitle">
          Speak or type your preferences. Our AI will search properties, check nearby amenities, 
          and give you neighborhood insights — all in one conversation.
        </p>
      </div>

      {/* Main Action Card */}
      <div className="landing-card glass-card animate-fade-in-up" style={{ animationDelay: '100ms' }}>
        {/* Voice Button */}
        <button 
          className="landing-voice-btn"
          onClick={() => onStartConversation()}
        >
          <div className="landing-voice-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <span className="landing-voice-text">Start Voice Search</span>
          <span className="landing-voice-hint">Click to speak with the AI assistant</span>
        </button>

        {/* Divider */}
        <div className="landing-divider">
          <span>or type your requirements</span>
        </div>

        {/* Text Input */}
        <div className="landing-input-row">
          <input
            type="text"
            className="input landing-input"
            placeholder="e.g. 2BHK in Koramangala under 35k..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button 
            className="btn btn-primary landing-send-btn"
            onClick={handleSend}
            disabled={!inputValue.trim()}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="landing-quick-actions animate-fade-in-up" style={{ animationDelay: '200ms' }}>
        <div className="landing-section-label">Quick Actions</div>
        <div className="landing-actions-row">
          <button className="landing-action-card" onClick={() => onStartConversation()}>
            <span className="landing-action-icon">🔍</span>
            <span className="landing-action-title">Find a Property</span>
            <span className="landing-action-desc">Search with voice or text</span>
          </button>
          <button className="landing-action-card" onClick={onManageBooking}>
            <span className="landing-action-icon">📅</span>
            <span className="landing-action-title">Manage Booking</span>
            <span className="landing-action-desc">Reschedule or cancel a visit</span>
          </button>
        </div>
      </div>

      {/* Popular Searches */}
      <div className="landing-popular animate-fade-in-up" style={{ animationDelay: '300ms' }}>
        <div className="landing-section-label">Popular Searches</div>
        <div className="landing-chips">
          {POPULAR_SEARCHES.map((search) => (
            <button
              key={search}
              className="chip landing-chip"
              onClick={() => onStartConversation(search)}
            >
              {search}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
