import { useState, useCallback, useEffect, useRef } from 'react';
import { Header } from './components/Header/Header';
import { LandingPage } from './components/LandingPage/LandingPage';
import { ConversationPane } from './components/ConversationPane/ConversationPane';
import { PropertyPane } from './components/PropertyPane/PropertyPane';
import { CompareView } from './components/PropertyPane/CompareView';
import { BookingModal } from './components/BookingModal/BookingModal';
import { ManageBookingModal } from './components/BookingModal/ManageBookingModal';
import { useConversation } from './hooks/useConversation';
import { useVoiceActivityDetection } from './hooks/useVoiceActivityDetection';
import './components/BookingModal/BookingModal.css';

type AppView = 'landing' | 'conversation';

function App() {
  const [currentView, setCurrentView] = useState<AppView>('landing');
  const [interimText, setInterimText] = useState('');

  // Modals state
  const [showManageBooking, setShowManageBooking] = useState(false);
  const [bookingPropertyId, setBookingPropertyId] = useState<string | null>(null);
  const [comparingIds, setComparingIds] = useState<string[]>([]);
  const [showCompare, setShowCompare] = useState(false);

  const {
    initSession,
    messages,
    isBotSpeaking,
    shortlist,
    preferences,
    hasPerformedSearch,
    sendTextMessage,
    sendAudioData,
    triggerGreeting,
    interruptBot,
    removeFilter,
    unlockAudio,
  } = useConversation({});

  const { isRecording, toggleListening, isLoading, vadState } = useVoiceActivityDetection({
    isBotSpeaking,
    onSpeechStart: () => {
      // Barge-in: if user starts talking, instantly stop the bot
      interruptBot();
    },
    onSpeechEnd: (audioBlob) => {
      setInterimText(''); // Clear interim when speech ends
      sendAudioData(audioBlob);
    },
    onInterimText: (text) => {
      setInterimText(text);
    },
    onFinalText: (text) => {
      setInterimText('');
      if (text.trim()) {
        sendTextMessage(text.trim());
      }
    },
  });

  // Remove toggleListeningRef as it is no longer needed for auto-activation

  // Initialize session on mount
  useEffect(() => {
    initSession();
  }, [initSession]);

  // Global user interaction listener to unlock AudioContext immediately on first click/tap
  useEffect(() => {
    const handleFirstInteraction = () => {
      unlockAudio();
      window.removeEventListener('click', handleFirstInteraction);
      window.removeEventListener('touchstart', handleFirstInteraction);
      window.removeEventListener('keydown', handleFirstInteraction);
    };
    window.addEventListener('click', handleFirstInteraction);
    window.addEventListener('touchstart', handleFirstInteraction);
    window.addEventListener('keydown', handleFirstInteraction);
    return () => {
      window.removeEventListener('click', handleFirstInteraction);
      window.removeEventListener('touchstart', handleFirstInteraction);
      window.removeEventListener('keydown', handleFirstInteraction);
    };
  }, [unlockAudio]);

  // If we restored a session that already has messages, skip the landing page
  useEffect(() => {
    if (messages.length > 0 && currentView === 'landing') {
      setCurrentView('conversation');
    }
  }, [messages.length, currentView]);

  const hasAutoStartedRef = useRef(false);

  // Auto-start microphone ONLY ONCE when entering conversation view and VAD is ready
  useEffect(() => {
    if (currentView === 'conversation' && !isRecording && !isLoading && !hasAutoStartedRef.current) {
      hasAutoStartedRef.current = true;
      toggleListening();
    }
  }, [currentView, isRecording, toggleListening, isLoading]);

  const handleStartConversation = useCallback((initialMessage?: string) => {
    // Unlock AudioContext synchronously during the user gesture so browser
    // autoplay policy doesn't block the bot's async voice response.
    unlockAudio();
    setCurrentView('conversation');
    if (initialMessage) {
      sendTextMessage(initialMessage);
    } else {
      // Trigger the spoken voice greeting from the bot
      triggerGreeting();
    }
  }, [sendTextMessage, triggerGreeting, unlockAudio]);

  const handleSendMessage = useCallback((text: string) => {
    sendTextMessage(text);
  }, [sendTextMessage]);

  const handleManageBooking = () => setShowManageBooking(true);

  const handleToggleCompare = (id: string) => {
    setComparingIds(prev =>
      prev.includes(id) ? prev.filter(pid => pid !== id) : [...prev, id]
    );
  };

  const handleStartVoice = () => {
    if (!isRecording) toggleListening();
  };
  const handleStopVoice = () => {
    if (isRecording) toggleListening();
  };

  return (
    <div className="app-layout">
      <Header onManageBooking={handleManageBooking} />

      {currentView === 'landing' && (
        <LandingPage
          onStartConversation={handleStartConversation}
          onManageBooking={handleManageBooking}
        />
      )}

      {currentView === 'conversation' && (
        <main className={`app-main ${hasPerformedSearch ? 'split-pane' : 'full-width'}`}>
          <ConversationPane
            messages={messages}
            onSendMessage={handleSendMessage}
            onStartVoice={handleStartVoice}
            onStopVoice={handleStopVoice}
            isListening={isRecording}
            isBotSpeaking={isBotSpeaking}
            hasShortlist={hasPerformedSearch}
            interimText={interimText}
            preferences={preferences}
            vadState={vadState}
          />

          {hasPerformedSearch && (
            <div className="pane">
              <PropertyPane
                properties={shortlist}
                preferences={preferences}
                onBookVisit={(id) => setBookingPropertyId(id)}
                onCompareToggle={handleToggleCompare}
                comparingIds={comparingIds}
                onShowCompare={() => setShowCompare(true)}
                onRemoveFilter={removeFilter}
              />
            </div>
          )}
        </main>
      )}

      {/* Modals */}
      {showManageBooking && (
        <ManageBookingModal onClose={() => setShowManageBooking(false)} />
      )}

      {bookingPropertyId && (
        <BookingModal
          propertyId={bookingPropertyId}
          onClose={() => setBookingPropertyId(null)}
        />
      )}

      {showCompare && (
        <CompareView
          properties={shortlist.filter(p => comparingIds.includes(p.id))}
          onClose={() => setShowCompare(false)}
        />
      )}
    </div>
  );
}

export default App;
