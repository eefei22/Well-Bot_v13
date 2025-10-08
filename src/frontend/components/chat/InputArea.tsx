import React, { useState } from 'react'
import styles from '@/styles/InputArea.module.css'

interface InputAreaProps {
  onSendMessage: (text: string) => void;
  disabled?: boolean;
}

export default function InputArea({ onSendMessage, disabled = false }: InputAreaProps) {
  const [text, setText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim() && !disabled) {
      onSendMessage(text.trim());
      setText('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className={styles.inputArea} onSubmit={handleSubmit}>
      <input
        type="text"
        className={styles.textInput}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Type a message..."
        disabled={disabled}
      />
      <button
        type="submit"
        className={styles.sendButton}
        disabled={disabled || !text.trim()}
      >
        →
      </button>
    </form>
  )
}
