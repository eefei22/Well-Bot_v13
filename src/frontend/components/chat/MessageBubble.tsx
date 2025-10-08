import React from 'react'
import styles from '@/styles/MessageBubble.module.css'

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  text: string;
  timestamp?: Date;
}

export default function MessageBubble({ role, text, timestamp }: MessageBubbleProps) {
  const bubbleClass = role === 'user' ? styles.userBubble : styles.assistantBubble;
  
  return (
    <div className={`${styles.messageBubble} ${bubbleClass}`}>
      <div>{text}</div>
      {timestamp && (
        <div className={styles.timestamp}>
          {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      )}
    </div>
  )
}
