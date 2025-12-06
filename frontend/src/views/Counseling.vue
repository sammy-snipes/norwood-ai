<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useCounselingStore } from '../stores/counseling'
import AppHeader from '../components/AppHeader.vue'
import HistorySidebar from '../components/HistorySidebar.vue'
import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
})

const authStore = useAuthStore()
const counselingStore = useCounselingStore()

const renderMarkdown = (content) => {
  return marked.parse(content || '')
}

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const sessions = ref([])
const activeSession = ref(null)
const messages = ref([])
const newMessage = ref('')
const loading = ref(false)
const messagesContainer = ref(null)

const isPremium = computed(() => authStore.user?.is_premium || authStore.user?.is_admin)

// Check if the current active session has any pending messages
const sending = computed(() => {
  return counselingStore.hasPendingMessages(activeSession.value)
})

const fetchSessions = async () => {
  try {
    const res = await fetch(`${API_URL}/api/counseling/sessions`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      sessions.value = await res.json()
    }
  } catch (err) {
    console.error('Failed to fetch sessions:', err)
  }
}

const createSession = async () => {
  try {
    const res = await fetch(`${API_URL}/api/counseling/sessions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      const session = await res.json()
      sessions.value.unshift(session)
      selectSession(session.id)
    }
  } catch (err) {
    console.error('Failed to create session:', err)
  }
}

const handleMessageComplete = async ({ messageId, sessionId, status, content }) => {
  // Only update UI if still on the same session
  if (activeSession.value !== sessionId) return

  const msgIndex = messages.value.findIndex(m => m.id === messageId)
  if (msgIndex !== -1) {
    messages.value[msgIndex] = {
      ...messages.value[msgIndex],
      status,
      content
    }
  }

  // Refresh sessions to update title
  await fetchSessions()

  await nextTick()
  scrollToBottom()
}

const selectSession = async (sessionId) => {
  activeSession.value = sessionId
  counselingStore.lastActiveSessionId = sessionId
  loading.value = true
  try {
    const res = await fetch(`${API_URL}/api/counseling/sessions/${sessionId}`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      messages.value = data.messages

      // Check for any pending/processing messages and register them with the store
      for (const msg of data.messages) {
        if (msg.status === 'pending' || msg.status === 'processing') {
          // Only add if not already tracked
          if (!counselingStore.pendingMessages[msg.id]) {
            counselingStore.addPendingMessage(msg.id, sessionId, handleMessageComplete)
          }
        }
      }

      // Update callbacks for any existing pending messages in this session
      counselingStore.updateCallbacks(sessionId, handleMessageComplete)

      await nextTick()
      scrollToBottom()
    }
  } catch (err) {
    console.error('Failed to fetch session:', err)
  } finally {
    loading.value = false
  }
}

const sendMessage = async () => {
  if (!newMessage.value.trim() || sending.value) return

  const content = newMessage.value.trim()
  const sessionId = activeSession.value
  newMessage.value = ''

  try {
    const res = await fetch(`${API_URL}/api/counseling/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content })
    })
    if (res.ok) {
      const data = await res.json()

      // Only add to UI if still on the same session
      if (activeSession.value === sessionId) {
        messages.value.push(data.user_message)
        messages.value.push(data.assistant_message)
      }

      // Track the pending assistant message in the global store
      if (data.assistant_message.status === 'pending' || data.assistant_message.status === 'processing') {
        counselingStore.addPendingMessage(
          data.assistant_message.id,
          sessionId,
          handleMessageComplete
        )
      }

      await nextTick()
      scrollToBottom()
    }
  } catch (err) {
    console.error('Failed to send message:', err)
  }
}

const deleteSession = async (sessionId) => {
  try {
    await fetch(`${API_URL}/api/counseling/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (activeSession.value === sessionId) {
      activeSession.value = null
      messages.value = []
      // Clear any pending messages for this session from the store
      const pending = counselingStore.getPendingForSession(sessionId)
      for (const msg of pending) {
        counselingStore.removePendingMessage(msg.id)
      }
    }
  } catch (err) {
    console.error('Failed to delete session:', err)
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

onMounted(async () => {
  if (isPremium.value) {
    await fetchSessions()

    // Restore last active session if we had one
    if (counselingStore.lastActiveSessionId) {
      // Verify the session still exists
      const sessionExists = sessions.value.some(s => s.id === counselingStore.lastActiveSessionId)
      if (sessionExists) {
        await selectSession(counselingStore.lastActiveSessionId)
      }
    }
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <AppHeader />

    <!-- Paywall -->
    <div v-if="!isPremium" class="flex items-center justify-center min-h-[calc(100vh-41px)]">
      <div class="text-center">
        <p class="text-gray-400 text-sm mb-2">Counseling requires a premium subscription.</p>
        <router-link to="/settings" class="text-purple-400 text-xs hover:underline">
          Upgrade to Premium
        </router-link>
      </div>
    </div>

    <!-- Main Content -->
    <div v-else class="flex h-[calc(100vh-41px)]">
      <!-- Sessions Sidebar -->
      <HistorySidebar
        :items="sessions"
        :selected-id="activeSession"
        new-button-text="+ New Session"
        empty-text="No sessions yet"
        always-show
        @new="createSession"
        @select="(item) => selectSession(item.id)"
        @delete="deleteSession"
      >
        <template #title="{ item }">{{ item.title || 'New session' }}</template>
        <template #date="{ item }">{{ formatDate(item.created_at) }}</template>
      </HistorySidebar>

      <!-- Chat Area -->
      <main class="flex-1 flex flex-col min-h-0">
        <!-- No session selected -->
        <div v-if="!activeSession" class="flex-1 flex items-center justify-center">
          <p class="text-gray-600 text-[11px]">Select or create a session</p>
        </div>

        <!-- Messages -->
        <div v-else class="flex-1 flex flex-col min-h-0">
          <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
            <div v-if="loading" class="text-center text-gray-600 text-xs">Loading...</div>

            <div
              v-for="msg in messages"
              :key="msg.id"
              :class="msg.role === 'user' ? 'text-right' : ''"
            >
              <!-- Pending/Processing message -->
              <div
                v-if="msg.status === 'pending' || msg.status === 'processing'"
                class="inline-block px-3 py-2 rounded bg-gray-800 text-gray-500 text-xs"
              >
                Thinking...
              </div>

              <!-- Failed message -->
              <div
                v-else-if="msg.status === 'failed'"
                class="inline-block px-3 py-2 rounded bg-red-900/30 text-red-400 text-xs"
              >
                {{ msg.content || 'Failed to generate response' }}
              </div>

              <!-- Completed message -->
              <div
                v-else
                class="inline-block px-3 py-2 rounded text-xs text-left max-w-2xl"
                :class="msg.role === 'user'
                  ? 'bg-purple-600/20 text-gray-200'
                  : 'bg-gray-800 text-gray-300'"
              >
                <div class="markdown-content" v-html="renderMarkdown(msg.content)"></div>
              </div>
            </div>
          </div>

          <!-- Input -->
          <div class="border-t border-gray-800 p-3">
            <div class="flex gap-2 max-w-2xl mx-auto">
              <input
                v-model="newMessage"
                @keydown.enter="sendMessage"
                :disabled="sending"
                placeholder="Type a message..."
                class="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-gray-600"
              />
              <button
                @click="sendMessage"
                :disabled="sending || !newMessage.trim()"
                class="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs rounded transition-colors"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.markdown-content :deep(p) {
  margin-bottom: 0.5em;
}
.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-left: 1.25em;
  margin-bottom: 0.5em;
}
.markdown-content :deep(ul) {
  list-style-type: disc;
}
.markdown-content :deep(ol) {
  list-style-type: decimal;
}
.markdown-content :deep(li) {
  margin-bottom: 0.25em;
}
.markdown-content :deep(code) {
  background: rgba(0, 0, 0, 0.3);
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.9em;
}
.markdown-content :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  padding: 0.75em;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 0.5em;
}
.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
}
.markdown-content :deep(strong) {
  font-weight: 600;
}
.markdown-content :deep(em) {
  font-style: italic;
}
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  font-weight: 600;
  margin-bottom: 0.5em;
}
.markdown-content :deep(blockquote) {
  border-left: 2px solid rgba(139, 92, 246, 0.5);
  padding-left: 0.75em;
  margin-left: 0;
  color: #9ca3af;
  font-style: italic;
}
.markdown-content :deep(a) {
  color: #a78bfa;
  text-decoration: underline;
}
.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin: 0.75em 0;
}
</style>
