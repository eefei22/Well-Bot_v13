import React, { useEffect, useRef } from 'react'
import styles from '@/styles/ActiveChat.module.css'
import MessageBubble from './MessageBubble'
import Card from './Card'
import InputArea from './InputArea'
import { Message } from '@/types/api'

interface ActiveChatProps {
  messages: Message[];
  partialTranscript?: string;
  isRecording?: boolean;
  onStartRecording: () => void;
  onSendMessage: (text: string) => void;
}

export default function ActiveChat({ 
  messages, 
  partialTranscript, 
  isRecording = false,
  onStartRecording, 
  onSendMessage 
}: ActiveChatProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, partialTranscript]);

  return (
    <div className={styles.activeChat}>
      <div className={styles.header}>
        <h1 className={styles.title}>Well-Bot</h1>
        <button
          className={styles.startButton}
          onClick={onStartRecording}
          disabled={isRecording}
        >
          {isRecording ? 'Recording...' : 'Start'}
        </button>
      </div>

      <div className={styles.messagesArea}>
        {messages.map((message) => (
          <div key={message.id}>
            <MessageBubble
              role={message.role}
              text={message.text}
              timestamp={message.timestamp}
            />
            {message.card && <Card card={message.card} />}
          </div>
        ))}
        
        {partialTranscript && (
          <div className={styles.partialTranscript}>
            {partialTranscript}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <InputArea onSendMessage={onSendMessage} />
    </div>
  )
}
