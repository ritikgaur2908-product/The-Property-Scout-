import React, { useState } from 'react';

interface VoiceControlsProps {
  onSpeechStart?: () => void;
  onSpeechEnd?: (audioData: Blob | Float32Array) => void;
  isBotSpeaking?: boolean;
  onInterrupt?: () => void;
  isListening?: boolean;
  onToggleListening?: () => void;
}

export const VoiceControls: React.FC<VoiceControlsProps> = ({ 
  onInterrupt,
  isBotSpeaking = false,
  isListening = false,
  onToggleListening,
}) => {
  const [internalActive, setInternalActive] = useState(false);
  const active = isListening || internalActive;

  const handleClick = () => {
    if (onToggleListening) {
      onToggleListening();
    } else {
      setInternalActive(!internalActive);
    }
    if (isBotSpeaking && onInterrupt) {
      onInterrupt();
    }
  };

  return (
    <div className="flex flex-col items-center gap-4 p-4">
      <button
        onClick={handleClick}
        className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
          active 
            ? 'bg-red-500 animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.5)]' 
            : 'bg-gray-700 hover:bg-gray-600'
        }`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      </button>
      
      <p className="text-sm font-medium text-gray-300">
        {!active ? 'Click to Start Voice Assistant' : 'Listening...'}
      </p>
    </div>
  );
};
