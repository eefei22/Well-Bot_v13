import { ChatTurnRequest, CardEnvelope } from '../types/api'

// Use relative path - Vite proxy will route to backend
const API_BASE = import.meta.env.VITE_API_BASE || ''

export async function chatTurn(request: ChatTurnRequest): Promise<CardEnvelope> {
  try {
    const response = await fetch(`${API_BASE}/llm/chat/turn`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    // Check for HTTP errors
    if (!response.ok) {
      console.error(`HTTP ${response.status}:`, await response.text())
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    
    // Differentiate backend error envelope from network error
    if (data.status === "error") {
      console.error('Backend error:', data.error_code, data.body)
      return {
        ...data,
        meta: { ...data.meta, source: 'backend' }  // Mark as backend error
      }
    }
    
    return data
    
  } catch (error) {
    console.error('Network/fetch error:', error)
    
    // Return error card for network failures
    return {
      status: "error",
      type: "error_card",
      title: "Connection Error",
      body: "Unable to connect to the assistant. Please check your connection and try again.",
      meta: {
        kind: "error",
        source: 'network'  // Mark as network error
      },
      error_code: "NETWORK_ERROR"
    }
  }
}
