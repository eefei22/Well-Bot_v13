import React from 'react'
import styles from '@/styles/Card.module.css'
import { CardEnvelope } from '@/types/api'

interface CardProps {
  card: CardEnvelope;
}

export default function Card({ card }: CardProps) {
  const isError = card.status === "error"
  const errorSource = card.meta?.source  // 'backend' or 'network'
  
  return (
    <div className={`${styles.card} ${isError ? styles.errorCard : ''}`}>
      {isError && errorSource && (
        <div className={styles.errorBadge}>
          {errorSource === 'network' ? '🔌' : '⚠️'} {errorSource}
        </div>
      )}
      <div className={styles.cardTitle}>{card.title}</div>
      <div className={styles.cardBody}>{card.body}</div>
      {card.meta?.kind && (
        <div className={styles.cardBadge}>{card.meta.kind}</div>
      )}
    </div>
  )
}
