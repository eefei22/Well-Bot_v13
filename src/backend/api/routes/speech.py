"""
Speech processing endpoints for Well-Bot API.
Provides STT and TTS smoke test routes.
"""

import asyncio
import json
import structlog
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import Response
import sys
from pathlib import Path

# Add the backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from services.deepgram_stt import TranscriptEvent
from services.deepgram_tts import synthesize

logger = structlog.get_logger()
router = APIRouter()


@router.post("/speech/tts:test")
async def test_tts(text: str = "Hello from Well-Bot"):
    """
    Test TTS synthesis endpoint.
    
    Args:
        text: Text to synthesize (default: "Hello from Well-Bot")
        
    Returns:
        Audio response (MP3 format)
    """
    try:
        logger.info("TTS test request", text_length=len(text))
        
        # Synthesize text to speech
        audio_data = await synthesize(text)
        
        logger.info("TTS test successful", audio_size=len(audio_data))
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=tts_test.mp3"
            }
        )
        
    except Exception as e:
        logger.error("TTS test failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@router.websocket("/speech/stt:test")
async def test_stt(websocket: WebSocket):
    """
    Test STT streaming endpoint.
    
    Accepts binary PCM audio chunks (16-bit, mono) and returns live transcript messages.
    Expected format: {type: "partial"|"final", text: str, confidence: float?, channel: int?}
    """
    await websocket.accept()
    logger.info("STT test WebSocket connected")
    
    try:
        logger.info("Starting STT WebSocket handler with concurrent relay pattern")
        
        # Deepgram parameters matching raw PCM16 input format
        dg_params = {
            "model": "nova-2",
            "language": "en",
            "interim_results": True,
            "smart_format": True,
            "punctuate": True,
            # For raw PCM16 frames (no RIFF header):
            "encoding": "linear16",
            "sample_rate": 44100,
            "channels": 1,
        }
        
        logger.info(f"Deepgram parameters: {dg_params}")
        
        # Get Deepgram STT client
        from services.deepgram_stt import get_stt_client
        stt_client = get_stt_client()
        
        # Build WebSocket URL with parameters
        ws_url = stt_client._build_ws_url(**dg_params)
        headers = {"Authorization": f"Token {stt_client.api_key}"}
        
        logger.info(f"Connecting to Deepgram: {ws_url}")
        
        async with websockets.connect(ws_url, additional_headers=headers) as dg_ws:
            logger.info("Connected to Deepgram WebSocket")
            
            async def client_to_deepgram():
                """Forward client audio to Deepgram."""
                try:
                    logger.info("Starting client-to-Deepgram relay")
                    while True:
                        msg = await websocket.receive()
                        logger.debug(f"Received from client: type={msg.get('type')}, has_text={'text' in msg}, has_bytes={'bytes' in msg}")
                        
                        if msg.get("type") == "websocket.receive":
                            if msg.get("bytes") is not None:
                                # Forward binary audio to Deepgram
                                await dg_ws.send(msg["bytes"])
                                logger.debug(f"Forwarded audio chunk to Deepgram: {len(msg['bytes'])} bytes")
                            elif msg.get("text") is not None:
                                # Handle control messages
                                text = msg["text"]
                                logger.info(f"Received text from client: {text}")
                                if text.lower() == "stop" or text == '{"type": "CloseStream"}':
                                    logger.info("Sending CloseStream to Deepgram")
                                    await dg_ws.send(json.dumps({"type": "CloseStream"}))
                                    await asyncio.sleep(0.5)  # Give Deepgram time to process
                                    break
                        else:
                            # Client disconnected
                            logger.info("Client disconnected, sending CloseStream to Deepgram")
                            await dg_ws.send(json.dumps({"type": "CloseStream"}))
                            await asyncio.sleep(0.5)  # Give Deepgram time to process
                            break
                except WebSocketDisconnect:
                    logger.info("Client WebSocket disconnected, sending CloseStream to Deepgram")
                    await dg_ws.send(json.dumps({"type": "CloseStream"}))
                    await asyncio.sleep(0.5)  # Give Deepgram time to process
                except Exception as e:
                    logger.error(f"Error in client-to-Deepgram relay: {e}")
            
            async def deepgram_to_client():
                """Forward Deepgram transcripts to client."""
                try:
                    logger.info("Starting Deepgram-to-client relay")
                    event_count = 0
                    async for message in dg_ws:
                        event_count += 1
                        logger.info(f"DG RAW: {message}")  # Debug: log raw message
                        logger.info(f"Received event {event_count} from Deepgram: {message[:200]}...")
                        
                        try:
                            # Parse Deepgram message
                            data = json.loads(message)
                            
                            # Log first 3 events as requested
                            if event_count <= 3:
                                logger.info(f"Deepgram event {event_count}: {data}")
                            
                            # Parse transcript event
                            transcript_event = stt_client._parse_transcript_message(data)
                            
                            if transcript_event:
                                # Build response message
                                response = {
                                    "type": "final" if transcript_event.is_final else "partial",
                                    "text": str(transcript_event.text),
                                }
                                
                                # Add optional fields
                                if transcript_event.confidence is not None:
                                    response["confidence"] = float(transcript_event.confidence)
                                if transcript_event.channel is not None:
                                    response["channel"] = int(transcript_event.channel)
                                
                                # Send to client
                                await websocket.send_text(json.dumps(response))
                                logger.info(f"Sent transcript to client: {response}")
                                
                                # Placeholder for safety.check on final transcripts
                                if transcript_event.is_final:
                                    logger.info(
                                        "PLACEHOLDER: Would call safety.check on final transcript",
                                        text=transcript_event.text,
                                        confidence=transcript_event.confidence
                                    )
                                    # Note: Removed break to allow continued streaming until CloseStream acknowledgment
                            else:
                                logger.debug(f"No transcript event parsed from: {data}")
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse Deepgram message: {e}")
                            logger.warning(f"Raw message: {message}")
                        except Exception as e:
                            logger.error(f"Error processing Deepgram message: {e}")
                            
                except Exception as e:
                    logger.error(f"Error in Deepgram-to-client relay: {e}")
            
            # Run both relays concurrently
            logger.info("Starting concurrent relay tasks")
            await asyncio.gather(client_to_deepgram(), deepgram_to_client())
            logger.info("STT test completed successfully")
            
    except WebSocketDisconnect:
        logger.info("STT test WebSocket disconnected")
    except Exception as e:
        logger.error("STT test failed", error=str(e), error_type=type(e).__name__)
        try:
            error_response = json.dumps({
                "type": "error",
                "error": str(e)
            })
            await websocket.send_text(error_response)
        except Exception as e2:
            logger.error(f"Failed to send error response: {e2}")
            pass  # WebSocket might be closed