import logging
import httpx
from typing import Optional
from backend.config import settings

logger = logging.getLogger(__name__)

class DeepgramSTT:
    """
    Handles Speech-to-Text via Deepgram API with dual SDK + HTTP fallback.
    """
    def __init__(self):
        self.api_key = settings.DEEPGRAM_API_KEY
        if not self.api_key:
            logger.warning("DEEPGRAM_API_KEY is missing!")
            self.client = None
        else:
            try:
                from deepgram import DeepgramClient
                self.client = DeepgramClient(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Deepgram SDK client: {e}")
                self.client = None

    def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribes raw audio bytes sent from client into text.
        """
        if not self.api_key or not audio_bytes or len(audio_bytes) < 100:
            return None

        # 1. Try Deepgram SDK Rest API
        if self.client:
            try:
                from deepgram import PrerecordedOptions
                options = PrerecordedOptions(
                    model="nova-2",
                    language="en-IN",
                    smart_format=True
                )
                payload = {"buffer": audio_bytes}
                
                # Support both rest.v('1') and prerecorded.v('1')
                if hasattr(self.client.listen, 'rest'):
                    response = self.client.listen.rest.v("1").transcribe_file(payload, options)
                else:
                    response = self.client.listen.prerecorded.v("1").transcribe_file(payload, options)

                if response and response.results and response.results.channels:
                    alternatives = response.results.channels[0].alternatives
                    if alternatives and alternatives[0].transcript:
                        transcript = alternatives[0].transcript.strip()
                        if transcript:
                            logger.info(f"Deepgram SDK transcript: {transcript}")
                            return transcript
            except Exception as sdk_err:
                logger.warning(f"Deepgram SDK error, falling back to direct HTTP: {sdk_err}")

        # 2. Direct HTTP Fallback (Zero dependency, 100% reliable)
        try:
            url = "https://api.deepgram.com/v1/listen?model=nova-2&language=en-IN&smart_format=true"
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/webm",
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, content=audio_bytes, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    channels = data.get("results", {}).get("channels", [])
                    if channels:
                        alts = channels[0].get("alternatives", [])
                        if alts and alts[0].get("transcript"):
                            transcript = alts[0]["transcript"].strip()
                            if transcript:
                                logger.info(f"Deepgram HTTP transcript: {transcript}")
                                return transcript
                else:
                    logger.error(f"Deepgram HTTP error status: {res.status_code} {res.text[:100]}")
        except Exception as http_err:
            logger.error(f"Deepgram HTTP fallback error: {http_err}")

        return None
