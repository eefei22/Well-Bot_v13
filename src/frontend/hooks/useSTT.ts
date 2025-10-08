import { useState, useRef, useCallback, useEffect } from 'react'
import { TranscriptEvent } from '../types/api'

interface UseSTTReturn {
  isConnected: boolean;
  transcripts: TranscriptEvent[];
  connect: () => void;
  disconnect: () => void;
  sendAudioFrame: (int16Data: Int16Array) => void;
  clearTranscripts: () => void;
}

export function useSTT(): UseSTTReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [transcripts, setTranscripts] = useState<TranscriptEvent[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    try {
      const ws = new WebSocket('ws://localhost:8000/speech/stt:test');
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('STT WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // data: {type: "partial"|"final", text: string, confidence?: number}
          
          const transcript: TranscriptEvent = {
            type: data.type,
            text: data.text,
            confidence: data.confidence
          };

          setTranscripts(prev => [...prev, transcript]);
        } catch (error) {
          console.error('Failed to parse STT message:', error);
        }
      };

      ws.onclose = () => {
        console.log('STT WebSocket disconnected');
        setIsConnected(false);
      };

      ws.onerror = (error) => {
        console.error('STT WebSocket error:', error);
        setIsConnected(false);
      };

    } catch (error) {
      console.error('Failed to connect STT WebSocket:', error);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      // Send CloseStream message before closing
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'CloseStream' }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendAudioFrame = useCallback((int16Data: Int16Array) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(int16Data.buffer);
    }
  }, []);

  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    transcripts,
    connect,
    disconnect,
    sendAudioFrame,
    clearTranscripts
  };
}
