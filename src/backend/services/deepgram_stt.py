"""
Deepgram Speech-to-Text service adapter.
Provides WebSocket streaming STT for real-time audio transcription.
"""

import json
import os
import structlog
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = structlog.get_logger()


@dataclass
class TranscriptEvent:
    """Normalized transcript event from Deepgram."""
    is_final: bool
    text: str
    channel: Optional[int] = None
    confidence: Optional[float] = None
    raw: Optional[Dict[str, Any]] = None


class DeepgramSTTClient:
    """Deepgram STT WebSocket client."""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is required")
        
        # Default configuration
        self.model = os.getenv("DEEPGRAM_STT_MODEL", "nova-2")
        self.language = os.getenv("DEEPGRAM_LANGUAGE", "en")
        self.punctuate = os.getenv("DEEPGRAM_PUNCTUATE", "true").lower() == "true"
        self.interim_results = os.getenv("DEEPGRAM_INTERIM_RESULTS", "true").lower() == "true"
        self.smart_format = os.getenv("DEEPGRAM_SMART_FORMAT", "true").lower() == "true"
        
        self.ws_url = "wss://api.deepgram.com/v1/listen"
    
    def _build_ws_url(self, **overrides) -> str:
        """Build WebSocket URL with query parameters."""
        params = {
            "model": overrides.get("model", self.model),
            "language": overrides.get("language", self.language),
            "punctuate": str(overrides.get("punctuate", self.punctuate)).lower(),
            "interim_results": str(overrides.get("interim_results", self.interim_results)).lower(),
            "smart_format": str(overrides.get("smart_format", self.smart_format)).lower(),
        }
        
        # Add audio format parameters if provided
        if "container" in overrides:
            params["container"] = overrides["container"]
        if "encoding" in overrides:
            params["encoding"] = overrides["encoding"]
        if "sample_rate" in overrides:
            params["sample_rate"] = str(overrides["sample_rate"])
        if "channels" in overrides:
            params["channels"] = str(overrides["channels"])

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.ws_url}?{query_string}"
    
    
    def _parse_transcript_message(self, data: Dict[str, Any]) -> Optional[TranscriptEvent]:
        """Parse Deepgram transcript message into normalized event."""
        try:
            # Deepgram response structure
            if "channel" in data and "alternatives" in data["channel"]:
                channel_data = data["channel"]
                alternatives = channel_data["alternatives"]
                
                if alternatives:
                    alternative = alternatives[0]
                    text = alternative.get("transcript", "")
                    confidence = alternative.get("confidence")
                    
                    # Determine if this is final
                    is_final = data.get("is_final", False)
                    
                    return TranscriptEvent(
                        is_final=is_final,
                        text=text,
                        channel=channel_data.get("index"),
                        confidence=confidence,
                        raw=data
                    )
                    
        except (KeyError, TypeError) as e:
            logger.warning("Failed to parse transcript message", error=str(e), data=data)
            
        return None


# Global client instance
_stt_client: Optional[DeepgramSTTClient] = None


def get_stt_client() -> DeepgramSTTClient:
    """Get global Deepgram STT client instance."""
    global _stt_client
    if _stt_client is None:
        _stt_client = DeepgramSTTClient()
    return _stt_client