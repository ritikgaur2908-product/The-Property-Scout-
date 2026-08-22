import React, { useState, useRef } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';

interface VoiceControlsProps {
  onSpeechStart: () => void;
  onSpeechEnd: (audioData: Float32Array) => void;
  isBotSpeaking: boolean;
  onInterrupt: () => void;
}

export const VoiceControls: React.FC<VoiceControlsProps> = ({ 
  onSpeechStart, 
  onSpeechEnd, 
  isBotSpeaking,
  onInterrupt
}) => {
  const [isActive, setIsActive] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);

  const vad = useMicVAD({
    startOnLoad: false,
    onSpeechStart: () => {
      // If the user starts talking while the bot is speaking, it's a barge-in (interruption)
      if (isBotSpeaking) {
        onInterrupt();
      }
      onSpeechStart();
    },
    onSpeechEnd: (audio) => {
      onSpeechEnd(audio);
    },
    // Customize VAD sensitivity
    positiveSpeechThreshold: 0.8,
    negativeSpeechThreshold: 0.8 - 0.15,
  });

  const toggleMicrophone = async () => {
    if (isActive) {
      vad.pause();
      setIsActive(false);
    } else {
      if (!audioContextRef.current) {
         audioContextRef.current = new window.AudioContext();
      }
      await audioContextRef.current.resume();
      vad.start();
      setIsActive(true);
    }
  };

  return (
    <div className="flex flex-col items-center gap-4 p-4">
      <button
        onClick={toggleMicrophone}
        className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
          isActive 
            ? vad.userSpeaking 
              ? 'bg-red-500 animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.5)]' 
              : 'bg-green-500 shadow-[0_0_15px_rgba(34,197,94,0.5)]'
            : 'bg-gray-700 hover:bg-gray-600'
        }`}
      >
        {/* Simple mic icon SVG */}
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      </button>
      
      <p className="text-sm font-medium text-gray-300">
        {!isActive 
          ? 'Click to Start Voice Assistant' 
          : vad.userSpeaking 
            ? 'Listening...' 
            : 'Waiting for speech...'}
      </p>
    </div>
  );
};
