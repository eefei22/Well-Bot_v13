#!/usr/bin/env python3
"""
CLI sanity test for Deepgram STT WebSocket endpoint.
Streams a WAV file to the STT test endpoint and prints transcripts.
"""

import asyncio
import json
import sys
import wave
import websockets
from pathlib import Path


async def stream_wav_to_stt(wav_path: str, ws_url: str = "ws://localhost:8080/speech/stt:test"):
    """
    Stream WAV file to STT WebSocket endpoint and print transcripts.
    
    Args:
        wav_path: Path to WAV file (should be mono, 16-bit PCM)
        ws_url: WebSocket URL for STT endpoint
    """
    print(f"Streaming {wav_path} to {ws_url}")
    
    try:
        # Open WAV file
        with wave.open(wav_path, 'rb') as wav_file:
            print(f"WAV info: {wav_file.getnchannels()} channels, {wav_file.getsampwidth()} bytes/sample, {wav_file.getframerate()} Hz")
            
            if wav_file.getnchannels() != 1:
                print("WARNING: WAV file should be mono (1 channel) for best results")
            
            if wav_file.getsampwidth() != 2:
                print("WARNING: WAV file should be 16-bit (2 bytes/sample) for best results")
            
            # Connect to WebSocket
            async with websockets.connect(ws_url) as websocket:
                print("Connected to STT WebSocket")
                
                # Start receiving messages
                receive_task = asyncio.create_task(receive_transcripts(websocket))
                
                # Stream audio data
                chunk_size = 1024  # Send in small chunks
                while True:
                    chunk = wav_file.readframes(chunk_size)
                    if not chunk:
                        break
                    
                    await websocket.send(chunk)
                    await asyncio.sleep(0.01)  # Small delay between chunks
                
                print("Finished sending audio data")
                
                # Wait for final transcript
                await receive_task
                
    except FileNotFoundError:
        print(f"ERROR: WAV file not found: {wav_path}")
        sys.exit(1)
    except websockets.exceptions.ConnectionRefused:
        print(f"ERROR: Could not connect to {ws_url}")
        print("Make sure the FastAPI server is running on localhost:8080")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


async def receive_transcripts(websocket):
    """Receive and print transcript messages from WebSocket."""
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                transcript_type = data.get("type", "unknown")
                text = data.get("text", "")
                confidence = data.get("confidence")
                
                if transcript_type == "partial":
                    print(f"[PARTIAL] {text}")
                elif transcript_type == "final":
                    print(f"[FINAL] {text}")
                    if confidence is not None:
                        print(f"         Confidence: {confidence:.2f}")
                    break  # End after final transcript
                elif transcript_type == "error":
                    print(f"[ERROR] {data.get('error', 'Unknown error')}")
                    break
                    
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse message: {e}")
                print(f"Raw message: {message}")
                
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"Error receiving transcripts: {e}")


def main():
    """Main CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/stt_ws_sanity.py <path_to_wav_file>")
        print("Example: python scripts/stt_ws_sanity.py sample.wav")
        sys.exit(1)
    
    wav_path = sys.argv[1]
    
    # Check if file exists
    if not Path(wav_path).exists():
        print(f"ERROR: File does not exist: {wav_path}")
        sys.exit(1)
    
    # Run the async function
    asyncio.run(stream_wav_to_stt(wav_path))


if __name__ == "__main__":
    main()
