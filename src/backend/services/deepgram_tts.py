"""
Deepgram Text-to-Speech service adapter.
Provides HTTP TTS synthesis with configurable voice and format.
"""

import os
import structlog
import aiohttp
from typing import Optional

logger = structlog.get_logger()


class DeepgramTTSClient:
    """Deepgram TTS HTTP client."""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is required")
        
        # Default configuration
        self.voice = os.getenv("DEEPGRAM_TTS_VOICE", "aura-asteria-en")
        self.format = os.getenv("DEEPGRAM_TTS_FORMAT", "mp3")
        
        self.base_url = "https://api.deepgram.com/v1/speak"
    
    async def synthesize(
        self, 
        text: str, 
        *, 
        voice: Optional[str] = None,
        format: Optional[str] = None
    ) -> bytes:
        """
        Synthesize text to speech audio.
        
        Args:
            text: Text to synthesize
            voice: Voice model (default: aura-asteria-en)
            format: Audio format (default: mp3)
            
        Returns:
            bytes: Raw audio data
        """
        voice_model = voice or self.voice
        audio_format = format or self.format
        
        # Build URL with model parameter
        url = f"{self.base_url}?model={voice_model}"
        
        # Prepare headers
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": f"audio/{audio_format}"
        }
        
        # Prepare request body
        body = {"text": text}
        
        logger.info("Synthesizing TTS", text_length=len(text), voice=voice_model, format=audio_format)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=body, headers=headers) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        logger.info("TTS synthesis successful", audio_size=len(audio_data))
                        return audio_data
                    else:
                        error_text = await response.text()
                        logger.error("TTS synthesis failed", status=response.status, error=error_text)
                        raise Exception(f"Deepgram TTS failed: {response.status} - {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error("TTS request failed", error=str(e))
            raise Exception(f"TTS request failed: {str(e)}")
        except Exception as e:
            logger.error("Unexpected TTS error", error=str(e))
            raise


# Global client instance
_tts_client: Optional[DeepgramTTSClient] = None


def get_tts_client() -> DeepgramTTSClient:
    """Get global Deepgram TTS client instance."""
    global _tts_client
    if _tts_client is None:
        _tts_client = DeepgramTTSClient()
    return _tts_client


async def synthesize(text: str, **kwargs) -> bytes:
    """Convenience function to synthesize text to speech."""
    client = get_tts_client()
    return await client.synthesize(text, **kwargs)
