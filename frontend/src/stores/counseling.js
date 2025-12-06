import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth'

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

/**
 * Global counseling store.
 *
 * Tracks pending messages and polls for their completion.
 * This allows the polling to continue even when navigating away.
 */
export const useCounselingStore = defineStore('counseling', () => {
  // Map of messageId -> { sessionId, callback }
  const pendingMessages = ref({})

  // Track the last active session so we can restore it on navigation
  const lastActiveSessionId = ref(null)

  let pollInterval = null
  const POLL_INTERVAL_MS = 1000

  function addPendingMessage(messageId, sessionId, onComplete) {
    pendingMessages.value[messageId] = {
      sessionId,
      callback: onComplete
    }
    startPolling()
  }

  function removePendingMessage(messageId) {
    delete pendingMessages.value[messageId]
    if (Object.keys(pendingMessages.value).length === 0) {
      stopPolling()
    }
  }

  function hasPendingMessages(sessionId = null) {
    if (sessionId === null) {
      return Object.keys(pendingMessages.value).length > 0
    }
    return Object.values(pendingMessages.value).some(m => m.sessionId === sessionId)
  }

  function getPendingForSession(sessionId) {
    return Object.entries(pendingMessages.value)
      .filter(([_, m]) => m.sessionId === sessionId)
      .map(([id, m]) => ({ id, ...m }))
  }

  function updateCallbacks(sessionId, newCallback) {
    for (const msg of Object.values(pendingMessages.value)) {
      if (msg.sessionId === sessionId) {
        msg.callback = newCallback
      }
    }
  }

  function startPolling() {
    if (pollInterval) return
    pollInterval = setInterval(pollAllMessages, POLL_INTERVAL_MS)
    pollAllMessages()
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  async function pollAllMessages() {
    const authStore = useAuthStore()
    const messageIds = Object.keys(pendingMessages.value)

    if (messageIds.length === 0) {
      stopPolling()
      return
    }

    for (const messageId of messageIds) {
      const msg = pendingMessages.value[messageId]
      if (!msg) continue

      try {
        const res = await fetch(`${API_URL}/api/counseling/messages/${messageId}/status`, {
          headers: { 'Authorization': `Bearer ${authStore.token}` }
        })

        if (res.ok) {
          const data = await res.json()

          if (data.status === 'completed' || data.status === 'failed') {
            const callback = msg.callback
            removePendingMessage(messageId)

            if (callback) {
              callback({
                messageId,
                sessionId: msg.sessionId,
                status: data.status,
                content: data.content
              })
            }
          }
        }
      } catch (err) {
        console.error(`Failed to poll message ${messageId}:`, err)
      }
    }
  }

  function cleanup() {
    stopPolling()
    pendingMessages.value = {}
  }

  return {
    pendingMessages,
    lastActiveSessionId,
    addPendingMessage,
    removePendingMessage,
    hasPendingMessages,
    getPendingForSession,
    updateCallbacks,
    cleanup
  }
})
