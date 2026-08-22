import logging
from typing import Optional
from deepgram import DeepgramClient
from backend.config import settings

logger = logging.getLogger(__name__)

class DeepgramSTT:
    """
    Handles Speech-to-Text via Deepgram API.
    """
    def __init__(self):
        if not settings.DEEPGRAM_API_KEY:
            logger.warning("DEEPGRAM_API_KEY is missing!")
            self.client = None
        else:
            self.client = DeepgramClient(api_key=settings.DEEPGRAM_API_KEY)

    def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribes raw audio WAV bytes sent from the client VAD into text.
        """
        if not self.client or not audio_bytes:
            return None

        try:
            response = self.client.listen.v1.media.transcribe_file(
                request=audio_bytes,
                model="nova-2",
                language="en-IN",
                smart_format=True
            )
            
            if response and response.results and response.results.channels:
                alternatives = response.results.channels[0].alternatives
                if alternatives:
                    transcript = alternatives[0].transcript
                    if transcript and transcript.strip():
                        logger.info(f"Deepgram STT transcript: {transcript}")
                        return transcript.strip()
        except Exception as e:
            logger.error(f"Deepgram STT error: {e}")
            
        return None
