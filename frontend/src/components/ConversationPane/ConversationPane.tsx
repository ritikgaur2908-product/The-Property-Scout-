import React, { useRef, useEffect, useState } from 'react';
import { DEFAULT_WELCOME_MESSAGE } from '../../hooks/useConversation';
import './ConversationPane.css';

export interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: Date;
}

interface ConversationPaneProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  onStartVoice: () => void;
  onStopVoice: () => void;
  isListening: boolean;
  isBotSpeaking: boolean;
  hasShortlist: boolean;
  /** Live interim transcript text as the user speaks */
  interimText?: string;
  preferences?: Record<string, any>;
  vadState?: 'idle' | 'listening' | 'speaking';
  onSpeakMessage?: (text: string) => void;
}

export const ConversationPane: React.FC<ConversationPaneProps> = ({
  messages,
  onSendMessage,
  onStartVoice,
  onStopVoice,
  isListening,
  isBotSpeaking,
  hasShortlist,
  interimText = '',
  preferences = {},
  vadState,
  onSpeakMessage,
}) => {
  const [inputValue, setInputValue] = useState('');
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const displayMessages = messages.length > 0 ? messages : [DEFAULT_WELCOME_MESSAGE];

  // Auto-scroll to bottom when new messages arrive or interim text changes
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayMessages, interimText]);

  const handleSend = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue.trim());
      setInputValue('');
      inputRef.current?.focus();
    }
  };

  const handleQuickAction = (action: string) => {
    onSendMessage(action);
  };

  const getDynamicChips = () => {
    const chips: string[] = [];
    if (!preferences.min_bhk) chips.push("Looking for a 2 BHK");
    if (!preferences.max_budget) chips.push("Budget under 40k");
    if (!preferences.parking) chips.push("I need parking");
    if (!preferences.gender) chips.push("Girls only flat");
    if (!preferences.food) chips.push("Vegetarian flatmates only");
    
    // Fill up to 4 chips with amenity questions if space permits
    if (chips.length < 4) chips.push("Hospitals nearby");
    if (chips.length < 4) chips.push("Metro nearby");
    
    return chips.slice(0, 4);
  };

  return (
    <div className="conversation-pane">
      {/* Pane Header */}
      <div className="conv-header">
        <div className="conv-header-left">
          <span className="conv-header-icon">🎙️</span>
          <h2 className="conv-header-title">AI Assistant</h2>
        </div>
        {isBotSpeaking && (
          <div className="conv-speaking-indicator">
            <div className="conv-speaking-dot"></div>
            <div className="conv-speaking-dot"></div>
            <div className="conv-speaking-dot"></div>
          </div>
        )}
        {isListening && !isBotSpeaking && (
          <div className={`conv-listening-badge ${vadState === 'speaking' ? 'conv-vad-speaking' : ''}`}>
            <span className="conv-listening-dot" />
            {vadState === 'speaking' ? 'Speaking...' : 'Listening...'}
          </div>
        )}
      </div>

      {/* Transcript List */}
      <div className="conv-transcript">
        {displayMessages.map((msg) => (
          <div
            key={msg.id}
            className={`conv-message animate-fade-in-up ${msg.sender}`}
          >
            {msg.sender === 'bot' && (
              <div className="conv-avatar conv-avatar-bot">🤖</div>
            )}
            <div className={`conv-bubble conv-bubble-${msg.sender}`}>
              <p>{msg.text}</p>
              <div className="flex items-center justify-between gap-2 mt-1">
                <span className="conv-time">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                {msg.sender === 'bot' && onSpeakMessage && (
                  <button
                    onClick={() => onSpeakMessage(msg.text)}
                    className="text-xs px-2 py-0.5 rounded bg-purple-900/40 hover:bg-purple-800/60 text-purple-300 transition-all flex items-center gap-1 border border-purple-500/30"
                    title="Read Aloud"
                  >
                    🔊 Listen
                  </button>
                )}
              </div>
            </div>
            {msg.sender === 'user' && (
              <div className="conv-avatar conv-avatar-user">👤</div>
            )}
          </div>
        ))}

        {/* Live interim transcription bubble — appears as user speaks */}
        {interimText && (
          <div className="conv-message animate-fade-in-up user">
            <div className="conv-bubble conv-bubble-user conv-bubble-interim">
              <p>{interimText}<span className="conv-cursor">|</span></p>
            </div>
            <div className="conv-avatar conv-avatar-user">👤</div>
          </div>
        )}

        <div ref={transcriptEndRef} />
      </div>

      {/* Quick Action Chips (shown only after shortlist is generated) */}
      {hasShortlist && (
        <div className="conv-quick-actions">
          {getDynamicChips().map((action) => (
            <button
              key={action}
              className="chip"
              onClick={() => handleQuickAction(action)}
            >
              {action}
            </button>
          ))}
        </div>
      )}

      {/* Audio Visualizer (shown when listening) */}
      {isListening && (
        <div className="conv-visualizer">
          {Array.from({ length: 9 }).map((_, i) => (
            <div
              key={i}
              className="conv-vis-bar"
              style={{ animationDelay: `${i * 0.08}s` }}
            />
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="conv-input-area">
        <input
          ref={inputRef}
          type="text"
          className="input conv-input"
          placeholder={isListening ? "Listening… speak now" : "Type your message…"}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />

        {/* Send Button */}
        <button
          className="btn btn-primary btn-icon conv-send-btn"
          onClick={handleSend}
          disabled={!inputValue.trim()}
          aria-label="Send message"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>

        {/* Mic Button */}
        <button
          className={`conv-mic-btn ${isListening ? 'conv-mic-active' : ''}`}
          onClick={isListening ? onStopVoice : onStartVoice}
          aria-label={isListening ? 'Stop listening' : 'Start voice input'}
        >
          {isListening ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
};
