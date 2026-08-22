import { useState, useCallback, useRef, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';
import { SessionAPI } from '../api/session';
import type { Message } from '../components/ConversationPane/ConversationPane';

export const DEFAULT_WELCOME_MESSAGE: Message = {
  id: 'welcome-0',
  sender: 'bot',
  text: "Hi! I'm your Property Scout. I'll help you find the perfect rental in Bengaluru. What are you looking for?",
  timestamp: new Date(),
};

interface UseConversationOptions {
  /** Called when the bot finishes all queued audio — use to auto-activate mic */
  onBotSpeakingEnd?: () => void;
}

export const useConversation = (options: UseConversationOptions = {}) => {
  const { onBotSpeakingEnd } = options;

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isBotSpeaking, setIsBotSpeaking] = useState(false);
  const [shortlist, setShortlist] = useState<any[]>([]);
  const [preferences, setPreferences] = useState<Record<string, any>>({});
  const [hasPerformedSearch, setHasPerformedSearch] = useState(false);

  // Pending greeting flag — send greeting once WS opens if start was clicked
  const pendingGreetingRef = useRef(false);

  // Sequential Audio Queue — prevents overlapping audio chunks
  const audioQueueRef = useRef<Blob[]>([]);
  const isPlayingAudioRef = useRef(false);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const onBotSpeakingEndRef = useRef(onBotSpeakingEnd);
  onBotSpeakingEndRef.current = onBotSpeakingEnd;

  const processAudioQueue = useCallback(() => {
    if (isPlayingAudioRef.current || audioQueueRef.current.length === 0) {
      return;
    }

    const nextBlob = audioQueueRef.current.shift();
    if (!nextBlob) return;

    isPlayingAudioRef.current = true;
    setIsBotSpeaking(true);

    const audioUrl = URL.createObjectURL(nextBlob);
    const audio = new Audio(audioUrl);
    currentAudioRef.current = audio;

    const onDone = () => {
      URL.revokeObjectURL(audioUrl);
      isPlayingAudioRef.current = false;
      currentAudioRef.current = null;
      if (audioQueueRef.current.length > 0) {
        processAudioQueue();
      } else {
        setIsBotSpeaking(false);
        // Auto-activate mic when bot finishes speaking
        onBotSpeakingEndRef.current?.();
      }
    };

    audio.onended = onDone;
    audio.onerror = onDone;

    audio.play().catch(err => {
      console.error("Audio playback error:", err);
      onDone();
    });
  }, []);

  // WebSocket URL once session is ready
  const wsUrl = sessionId
    ? `${(import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws')}/api/voice/stream?session_id=${sessionId}`
    : '';

  const { status, sendMessage, disconnect } = useWebSocket({
    url: wsUrl,
    reconnect: true,
    onMessage: (data) => {
      if (data instanceof Blob) {
        audioQueueRef.current.push(data);
        processAudioQueue();
      } else if (data.type === 'user_text') {
        setMessages(prev => [...prev, {
          id: `usr-${Date.now()}`,
          sender: 'user',
          text: data.content,
          timestamp: new Date(),
        }]);
      } else if (data.type === 'text') {
        setMessages(prev => {
          if (prev.some(m => m.text === data.content)) return prev;
          return [...prev, {
            id: `bot-${Date.now()}`,
            sender: 'bot',
            text: data.content,
            timestamp: new Date(),
          }];
        });
      } else if (data.type === 'shortlist') {
        setShortlist(data.properties);
        setHasPerformedSearch(true);
        if (data.preferences) {
          setPreferences(data.preferences);
        }
      } else if (data.type === 'property_update') {
        setShortlist(prev => prev.map(p => 
          p.id === data.property_id 
            ? { ...p, amenities: data.amenities, neighborhoodInsights: data.neighborhoodInsights }
            : p
        ));
      }
    },
    onOpen: () => {
      console.log('[WS] Connected');
      // If a greeting was requested before the WS was ready, send it now
      if (pendingGreetingRef.current) {
        pendingGreetingRef.current = false;
        console.log('[WS] Sending pending greeting');
        sendMessage({ type: 'greeting' });
      }
    },
    onError: (e) => {
      console.error('[WS] Error:', e);
    }
  });

  const interruptBot = useCallback(() => {
    console.log('[WS] Interrupting bot audio');
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingAudioRef.current = false;
    setIsBotSpeaking(false);
    
    // Send interrupt signal to backend so it stops TTS streaming
    if (status === 'connected') {
      sendMessage({ type: 'interrupt' });
    }
  }, [status, sendMessage]);

  // When WS becomes connected and greeting is pending, fire it
  useEffect(() => {
    if (status === 'connected' && pendingGreetingRef.current) {
      pendingGreetingRef.current = false;
      console.log('[WS] Status=connected, sending queued greeting');
      sendMessage({ type: 'greeting' });
    }
  }, [status, sendMessage]);

  const initSession = useCallback(async () => {
    try {
      const storedSessionId = localStorage.getItem('property_scout_session_id');

      if (storedSessionId) {
        try {
          const sessionData = await SessionAPI.getSession(storedSessionId);
          setSessionId(storedSessionId);

          if (sessionData.transcript && sessionData.transcript.length > 0) {
            setMessages(sessionData.transcript);
          }
          if (sessionData.shortlist) {
            setShortlist(sessionData.shortlist);
          }
          if (sessionData.preferences && Object.keys(sessionData.preferences).length > 0) {
            setPreferences(sessionData.preferences);
            setHasPerformedSearch(true);
          }
          return;
        } catch (err) {
          console.warn('Could not restore session, creating new one', err);
          localStorage.removeItem('property_scout_session_id');
        }
      }

      const response = await SessionAPI.createSession();
      setSessionId(response.session_id);
      localStorage.setItem('property_scout_session_id', response.session_id);
    } catch (error) {
      console.error('Failed to initialize session', error);
    }
  }, []);

  const sendTextMessage = useCallback((text: string) => {
    setMessages(prev => [...prev, {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date(),
    }]);

    if (status === 'connected') {
      sendMessage({ type: 'text', content: text });
    } else if (sessionId) {
      SessionAPI.sendMessage(sessionId, text)
        .then((res) => {
          if (res.response) {
            setMessages(prev => [...prev, {
              id: `bot-${Date.now()}`,
              sender: 'bot',
              text: res.response,
              timestamp: new Date(),
            }]);
          }
          if (res.shortlist) {
            setShortlist(res.shortlist);
          }
          if (res.preferences && Object.keys(res.preferences).length > 0) {
            setPreferences(res.preferences);
            setHasPerformedSearch(true);
          }
        })
        .catch(console.error);
    }
  }, [status, sendMessage, sessionId]);

  const removeFilter = useCallback(async (key: string, value?: string) => {
    if (!sessionId) return;
    try {
      const result = await SessionAPI.removeFilter(sessionId, key, value);
      setPreferences(result.preferences || {});
      setShortlist(result.shortlist || []);
      setHasPerformedSearch(true);
    } catch (error) {
      console.error('Failed to remove filter', error);
    }
  }, [sessionId]);

  const sendAudioData = useCallback((audioBlob: Blob) => {
    if (status === 'connected') {
      sendMessage(audioBlob);
    } else {
      console.warn('[WS] Not connected — cannot send audio.');
    }
  }, [status, sendMessage]);

  /**
   * Request a voice greeting from the bot.
   * If WS isn't ready yet, stores a flag and fires when connection opens.
   */
  const triggerGreeting = useCallback(() => {
    if (status === 'connected') {
      console.log('[WS] Sending greeting immediately');
      sendMessage({ type: 'greeting' });
    } else {
      console.log('[WS] Not yet connected — queuing greeting for onOpen');
      pendingGreetingRef.current = true;
    }
  }, [status, sendMessage]);

  return {
    sessionId,
    messages,
    isBotSpeaking,
    shortlist,
    preferences,
    hasPerformedSearch,
    wsStatus: status,
    initSession,
    sendTextMessage,
    sendAudioData,
    triggerGreeting,
    interruptBot,
    removeFilter,
    disconnect,
  };
};
