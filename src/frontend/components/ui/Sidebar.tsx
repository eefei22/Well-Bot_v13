import React from 'react'
import styles from '@/styles/Sidebar.module.css'

interface SidebarProps {
  activePage?: string;
  onPageChange?: (page: string) => void;
}

export default function Sidebar({ activePage = 'chat', onPageChange }: SidebarProps) {
  const navItems = [
    { id: 'chat', label: 'Chat' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'settings', label: 'Settings' }
  ];

  return (
    <div className={styles.sidebar}>
      {navItems.map(item => (
        <button
          key={item.id}
          className={`${styles.navButton} ${activePage === item.id ? styles.active : ''}`}
          onClick={() => onPageChange?.(item.id)}
        >
          {item.label}
        </button>
      ))}
      
      <button className={styles.logoutButton}>
        Logout
      </button>
    </div>
  )
}
