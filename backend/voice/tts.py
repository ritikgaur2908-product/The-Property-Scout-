import asyncio
import logging
import edge_tts

logger = logging.getLogger(__name__)


class IndianTTS:
    """
    Handles Text-to-Speech using Microsoft Edge TTS with Indian English voice.
    Free, unlimited, and uses en-IN-NeerjaExpressiveNeural — a warm,
    expressive Indian-accented female voice perfect for a Bengaluru property assistant.
    """

    def __init__(self, voice: str = "en-IN-NeerjaExpressiveNeural"):
        self.voice = voice

    def synthesize_sync(self, text: str) -> bytes:
        """
        Synchronously synthesizes text into MP3 audio bytes.
        Run in a thread pool via loop.run_in_executor() to avoid blocking asyncio.
        Returns empty bytes on error.
        """
        if not text or not text.strip():
            return b""
        try:
            return asyncio.run(self._synthesize(text.strip()))
        except Exception as e:
            logger.error(f"Edge TTS error for voice '{self.voice}': {e}")
            return b""

    async def _synthesize(self, text: str) -> bytes:
        """Internal async synthesis — collects all audio chunks into a single MP3 buffer."""
        communicate = edge_tts.Communicate(text, self.voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        if audio_bytes:
            logger.info(f"Edge TTS '{self.voice}': synthesized {len(audio_bytes)} bytes")
        return audio_bytes
