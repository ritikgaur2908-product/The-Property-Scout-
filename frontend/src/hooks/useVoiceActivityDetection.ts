import { useState, useCallback, useRef, useEffect } from 'react';

interface UseVoiceActivityDetectionProps {
  onSpeechStart?: () => void;
  onSpeechEnd?: (audioBlob: Blob) => void;
  onInterimText?: (text: string) => void;
  onFinalText?: (text: string) => void;
  isBotSpeaking?: boolean;
}

const SILENCE_THRESHOLD_MS = 1500; // 1.5 seconds of silence ends turn
const VOLUME_THRESHOLD = 8; // Highly sensitive to voice while ignoring baseline hiss
const SPEECH_FRAMES_REQUIRED = 2; // Fast speech trigger for short words like "2BHK"

export const useVoiceActivityDetection = ({
  onSpeechStart,
  onSpeechEnd,
  onInterimText,
  onFinalText,
  isBotSpeaking = false,
}: UseVoiceActivityDetectionProps) => {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  const chunksRef = useRef<Blob[]>([]);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rAFRef = useRef<number | null>(null);
  const consecutiveFramesRef = useRef(0);

  // Use a ref for isBotSpeaking to avoid stale closures in monitorVolume
  const isBotSpeakingRef = useRef(isBotSpeaking);
  useEffect(() => {
    isBotSpeakingRef.current = isBotSpeaking;
  }, [isBotSpeaking]);

  const startRecording = useCallback(() => {
    if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'recording') return;
    chunksRef.current = [];
    mediaRecorderRef.current.start();
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const monitorVolume = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate average volume
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i];
    }
    const average = sum / dataArray.length;

    setIsSpeaking((prevSpeaking) => {
      // If the bot is speaking, ignore all volume spikes to prevent self-interruption (echo loop)
      if (isBotSpeakingRef.current) {
        consecutiveFramesRef.current = 0;
        return false;
      }

      if (average > VOLUME_THRESHOLD) {
        consecutiveFramesRef.current += 1;

        if (consecutiveFramesRef.current >= SPEECH_FRAMES_REQUIRED) {
          // Human is definitely speaking
          if (!prevSpeaking) {
            console.log('[VAD] Speech started');
            onSpeechStart?.();
            startRecording();
          }

          // Reset silence timer
          if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = setTimeout(() => {
            console.log('[VAD] Speech ended due to silence');
            setIsSpeaking(false);
            stopRecording();
          }, SILENCE_THRESHOLD_MS);

          return true;
        }
      } else {
        // Reset consecutive frames if volume drops
        consecutiveFramesRef.current = Math.max(0, consecutiveFramesRef.current - 1);
      }
      return prevSpeaking;
    });

    rAFRef.current = requestAnimationFrame(monitorVolume);
  }, [onSpeechStart, startRecording, stopRecording]);

  const toggleListening = useCallback(async () => {
    if (isListening) {
      // Stop everything
      if (rAFRef.current) cancelAnimationFrame(rAFRef.current);
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      if (streamRef.current) {
        const recognition = (streamRef as any).recognition;
        if (recognition) {
          recognition.onend = null; // Prevent restart loop
          try { recognition.stop(); } catch (e) { }
        }
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      setIsListening(false);
      setIsSpeaking(false);
    } else {
      // Start listening
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          }
        });
        streamRef.current = stream;

        // Create audio context for volume analysis
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioContext = new AudioContextClass();
        audioContextRef.current = audioContext;

        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyserRef.current = analyser;

        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        // Create MediaRecorder to capture the raw audio chunks
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm'; // fallback

        const mediaRecorder = new MediaRecorder(stream, { mimeType });
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data);
        };

        mediaRecorder.onstop = () => {
          if (chunksRef.current.length > 0) {
            const blob = new Blob(chunksRef.current, { type: mediaRecorder.mimeType });
            onSpeechEnd?.(blob);
            chunksRef.current = [];
          }
        };

        const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        let recognition: any = null;
        if (SpeechRecognitionClass) {
          recognition = new SpeechRecognitionClass();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.onresult = (event: any) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              if (event.results[i].isFinal) {
                const finalPhrase = event.results[i][0].transcript.trim();
                if (finalPhrase && !isBotSpeakingRef.current) {
                  console.log('[VAD/STT] Final transcript captured:', finalPhrase);
                  onFinalText?.(finalPhrase);
                }
              } else {
                interim += event.results[i][0].transcript;
              }
            }
            if (interim && !isBotSpeakingRef.current) {
              onInterimText?.(interim);
            }
          };

          // Auto-restart if it dies while we are still supposed to be listening
          recognition.onend = () => {
            if (streamRef.current) {
              try { recognition.start(); } catch (e) { }
            }
          };

          try {
            recognition.start();
          } catch (e) {
            console.warn('SpeechRecognition failed to start', e);
          }
        }

        // Store recognition on streamRef temporarily so we can stop it later
        (streamRef as any).recognition = recognition;

        setIsListening(true);
        monitorVolume();
      } catch (err) {
        console.error('Failed to start mic', err);
      }
    }
  }, [isListening, monitorVolume, onSpeechEnd, onInterimText, onFinalText]);

  useEffect(() => {
    return () => {
      if (rAFRef.current) cancelAnimationFrame(rAFRef.current);
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (audioContextRef.current) audioContextRef.current.close();
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    };
  }, []);

  const vadState: 'idle' | 'listening' | 'speaking' = isListening
    ? (isSpeaking ? 'speaking' : 'listening')
    : 'idle';

  return {
    isRecording: isListening,
    toggleListening,
    vadState,
    isLoading: false, // native API loads instantly
    isErrored: false,
  };
};
