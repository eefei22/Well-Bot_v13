import React, { useState, useEffect } from 'react'
import styles from '@/styles/ChatHistory.module.css'

interface Conversation {
  id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

interface ChatHistoryProps {
  userId: string
  onSelectHistory?: (conversationId: string) => void
}

export default function ChatHistory({ userId, onSelectHistory }: ChatHistoryProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchConversations()
  }, [userId])

  const fetchConversations = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`/api/conversations/${userId}`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setConversations(data)
    } catch (err) {
      console.error('Failed to fetch conversations:', err)
      setError('Failed to load conversations')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className={styles.chatHistory}>
        <h2 className={styles.header}>Chat History</h2>
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <span>Loading conversations...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={styles.chatHistory}>
        <h2 className={styles.header}>Chat History</h2>
        <div className={styles.error}>
          <span>{error}</span>
          <button 
            className={styles.retryButton}
            onClick={fetchConversations}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (conversations.length === 0) {
    return (
      <div className={styles.chatHistory}>
        <h2 className={styles.header}>Chat History</h2>
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>💬</div>
          <span>No conversations yet</span>
          <p>Start a new conversation to see it here!</p>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.chatHistory}>
      <h2 className={styles.header}>Chat History</h2>
      <div className={styles.historyList}>
        {conversations.map(conversation => (
          <button
            key={conversation.id}
            className={styles.historyItem}
            onClick={() => onSelectHistory?.(conversation.id)}
            title={`${conversation.message_count} messages`}
          >
            <div className={styles.conversationTitle}>
              {conversation.title}
            </div>
            <div className={styles.conversationDate}>
              {formatDate(conversation.updated_at)}
            </div>
            <div className={styles.messageCount}>
              {conversation.message_count} messages
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}