import { useState, useRef, useCallback } from 'react'

interface UseAudioRecorderReturn {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  audioFrames: Int16Array[];
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [audioFrames, setAudioFrames] = useState<Int16Array[]>([]);
  
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const downsample = useCallback((buffer: Float32Array, fromRate: number, toRate: number): Float32Array => {
    if (fromRate === toRate) return buffer;
    
    const ratio = fromRate / toRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    
    for (let i = 0; i < newLength; i++) {
      const srcIndex = Math.floor(i * ratio);
      result[i] = buffer[srcIndex];
    }
    
    return result;
  }, []);

  const float32ToInt16 = useCallback((buffer: Float32Array): Int16Array => {
    const int16 = new Int16Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
      const s = Math.max(-1, Math.min(1, buffer[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16;
  }, []);

  const startRecording = useCallback(async () => {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000 // Request 16kHz if supported
        }
      });

      streamRef.current = stream;

      // Create audio context
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;

      // Create source from stream
      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      // Create script processor for raw audio
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      // Process audio chunks
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0); // Float32Array
        
        // Downsample if needed (browser native rate → 16kHz)
        const downsampled = downsample(inputData, audioContext.sampleRate, 16000);
        
        // Convert Float32 (-1 to 1) → Int16 (-32768 to 32767)
        const int16 = float32ToInt16(downsampled);
        
        // Store frame for sending
        setAudioFrames(prev => [...prev, int16]);
      };

      // Connect pipeline
      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
      setAudioFrames([]); // Clear previous frames

    } catch (error) {
      console.error('Failed to start recording:', error);
      throw error;
    }
  }, [downsample, float32ToInt16]);

  const stopRecording = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setIsRecording(false);
  }, []);

  return {
    isRecording,
    startRecording,
    stopRecording,
    audioFrames
  };
}
