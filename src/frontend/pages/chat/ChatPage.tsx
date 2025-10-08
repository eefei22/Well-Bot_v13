import React, { useState, useCallback, useEffect } from 'react'
import Layout from '@/components/ui/Layout'
import Sidebar from '@/components/ui/Sidebar'
import ChatHistory from '@/components/ui/ChatHistory'
import ActiveChat from '@/components/chat/ActiveChat'
import { useAudioRecorder } from '@/hooks/useAudioRecorder'
import { useSTT } from '@/hooks/useSTT'
import { chatTurn } from '@/services/api'
import { Message, SessionMetadata } from '@/types/api'

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [partialTranscript, setPartialTranscript] = useState<string>('');
  const [isRecording, setIsRecording] = useState(false);

  // Hardcoded session metadata for now
  const sessionMetadata: SessionMetadata = {
    user_id: '00000000-0000-0000-0000-000000000000',
    conversation_id: 'conv-123',
    session_id: 'session-456',
    trace_id: 'trace-789'
  };

  const { isRecording: audioRecording, startRecording, stopRecording, audioFrames } = useAudioRecorder();
  const { isConnected, transcripts, connect, disconnect, sendAudioFrame, clearTranscripts } = useSTT();

  // Send audio frames to STT when recording
  useEffect(() => {
    if (audioRecording && isConnected && audioFrames.length > 0) {
      const latestFrame = audioFrames[audioFrames.length - 1];
      sendAudioFrame(latestFrame);
    }
  }, [audioRecording, isConnected, audioFrames, sendAudioFrame]);

  // Handle STT transcripts
  useEffect(() => {
    if (transcripts.length > 0) {
      const latestTranscript = transcripts[transcripts.length - 1];
      
      if (latestTranscript.type === 'partial') {
        setPartialTranscript(latestTranscript.text);
      } else if (latestTranscript.type === 'final') {
        setPartialTranscript('');
        handleSendToLLM(latestTranscript.text);
      }
    }
  }, [transcripts]);

  const handleSendToLLM = useCallback(async (text: string) => {
    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      text,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);

    try {
      // Send to LLM
      const response = await chatTurn({
        text,
        ...sessionMetadata
      });

      // Add assistant message with card
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        text: response.body,
        timestamp: new Date(),
        card: response
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send to LLM:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        text: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    }
  }, [sessionMetadata]);

  const handleStartRecording = useCallback(async () => {
    try {
      await startRecording();
      connect();
      setIsRecording(true);
      clearTranscripts();
    } catch (error) {
      console.error('Failed to start recording:', error);
      alert('Failed to access microphone. Please check permissions.');
    }
  }, [startRecording, connect, clearTranscripts]);

  const handleStopRecording = useCallback(() => {
    stopRecording();
    disconnect();
    setIsRecording(false);
    setPartialTranscript('');
  }, [stopRecording, disconnect]);

  const handleSendMessage = useCallback((text: string) => {
    handleSendToLLM(text);
  }, [handleSendToLLM]);

  const handleSelectHistory = useCallback((conversationId: string) => {
    // TODO: Load conversation messages
    console.log('Selected conversation:', conversationId);
  }, []);

  return (
    <Layout>
      <Sidebar />
      <ChatHistory userId={sessionMetadata.user_id} onSelectHistory={handleSelectHistory} />
      <ActiveChat
        messages={messages}
        partialTranscript={partialTranscript}
        isRecording={isRecording}
        onStartRecording={handleStartRecording}
        onSendMessage={handleSendMessage}
      />
    </Layout>
  )
}
