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

  // AudioContext — unlocked on first user gesture, then free to play anytime.
  // This bypasses Chrome/Safari autoplay restrictions that block new Audio().play()
  // when called from an async WebSocket handler (gesture trust window already expired).
  const audioCtxRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingAudioRef = useRef(false);
  const onBotSpeakingEndRef = useRef(onBotSpeakingEnd);
  onBotSpeakingEndRef.current = onBotSpeakingEnd;

  /**
   * Call this synchronously inside a user gesture (button click) to unlock
   * the AudioContext so later async .play() calls succeed.
   */
  const unlockAudio = useCallback(() => {
    try {
      if (!audioCtxRef.current) {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          audioCtxRef.current = new AudioCtx();
        }
      }
      if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
        audioCtxRef.current.resume().catch(() => {});
      }
    } catch (e) {
      console.warn('AudioContext unlock warning:', e);
    }
  }, []);

  const processAudioQueue = useCallback(async () => {
    if (isPlayingAudioRef.current || audioQueueRef.current.length === 0) return;

    isPlayingAudioRef.current = true;
    setIsBotSpeaking(true);

    const nextBuffer = audioQueueRef.current.shift();
    if (!nextBuffer) {
      isPlayingAudioRef.current = false;
      setIsBotSpeaking(false);
      return;
    }

    const onDone = () => {
      isPlayingAudioRef.current = false;
      if (audioQueueRef.current.length > 0) {
        processAudioQueue();
      } else {
        setIsBotSpeaking(false);
        onBotSpeakingEndRef.current?.();
      }
    };

    // 1. Try Web Audio API playback
    try {
      if (!audioCtxRef.current) {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          audioCtxRef.current = new AudioCtx();
        }
      }
      if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
        await audioCtxRef.current.resume();
      }

      if (audioCtxRef.current) {
        // Clone buffer to prevent detaching original ArrayBuffer if decode fails
        const clone = nextBuffer.slice(0);
        const decoded = await audioCtxRef.current.decodeAudioData(clone);
        const source = audioCtxRef.current.createBufferSource();
        source.buffer = decoded;
        source.connect(audioCtxRef.current.destination);
        source.onended = onDone;
        activeSourceRef.current = source;
        source.start(0);
        return;
      }
    } catch (err) {
      console.warn('AudioContext decode failed, trying HTML5 Audio fallback:', err);
    }

    // 2. Fallback to HTML5 Audio element
    try {
      const blob = new Blob([nextBuffer], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); onDone(); };
      audio.onerror = () => { URL.revokeObjectURL(url); onDone(); };
      await audio.play();
    } catch (err) {
      console.error('All audio playback methods failed:', err);
      onDone();
    }
  }, []);

  // WebSocket URL once session is ready
  const defaultApiUrl = import.meta.env.VITE_API_URL || 'https://web-production-4b14e.up.railway.app';
  const wsUrl = sessionId
    ? `${defaultApiUrl.replace(/^http/, 'ws')}/api/voice/stream?session_id=${sessionId}&session_token=${sessionId}`
    : '';

  const { status, sendMessage, disconnect } = useWebSocket({
    url: wsUrl,
    reconnect: true,
    onMessage: (data) => {
      if (data instanceof Blob) {
        // Convert Blob -> ArrayBuffer for AudioContext.decodeAudioData
        data.arrayBuffer().then(buf => {
          audioQueueRef.current.push(buf);
          processAudioQueue();
        });
        return;
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

  // Track active AudioBufferSourceNode for barge-in interruption
  const activeSourceRef = useRef<AudioBufferSourceNode | null>(null);

  const interruptBot = useCallback(() => {
    console.log('[WS] Interrupting bot audio');
    if (activeSourceRef.current) {
      try { activeSourceRef.current.stop(); } catch (_) {}
      activeSourceRef.current = null;
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
    unlockAudio,
  };
};
