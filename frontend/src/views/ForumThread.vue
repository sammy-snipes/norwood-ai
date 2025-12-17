<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppHeader from '../components/AppHeader.vue'
import DonateToast from '../components/DonateToast.vue'
import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
})

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const thread = ref(null)
const loading = ref(true)
const newReply = ref('')
const sending = ref(false)
const showDonateToast = ref(false)
const replyingTo = ref(null) // For nested replies

// Polling for pending agent replies
let pollInterval = null
const pendingReplies = ref(new Set())

// Get display name for agents (looks like regular users)
const getDisplayName = (reply) => {
  if (reply.agent) {
    return reply.agent.display_name
  }
  return reply.user?.name || 'Anonymous'
}

const renderMarkdown = (content) => {
  return marked.parse(content || '')
}

const fetchThread = async () => {
  try {
    const res = await fetch(`${API_URL}/api/forum/threads/${route.params.threadId}`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      thread.value = await res.json()
      // Check for pending replies
      checkPendingReplies()
    } else if (res.status === 404) {
      router.push({ name: 'forum' })
    }
  } catch (err) {
    console.error('Failed to fetch thread:', err)
  } finally {
    loading.value = false
  }
}

const checkPendingReplies = () => {
  if (!thread.value?.replies) return

  const pending = thread.value.replies.filter(r =>
    r.status === 'pending' || r.status === 'processing'
  )

  if (pending.length > 0) {
    pendingReplies.value = new Set(pending.map(r => r.id))
    startPolling()
  } else {
    stopPolling()
  }
}

const startPolling = () => {
  if (pollInterval) return
  pollInterval = setInterval(pollPendingReplies, 2000)
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const pollPendingReplies = async () => {
  for (const replyId of pendingReplies.value) {
    try {
      const res = await fetch(`${API_URL}/api/forum/replies/${replyId}/status`, {
        headers: { 'Authorization': `Bearer ${authStore.token}` }
      })
      if (res.ok) {
        const data = await res.json()
        if (data.status === 'completed' || data.status === 'failed') {
          // Update the reply in the list
          const reply = thread.value.replies.find(r => r.id === replyId)
          if (reply) {
            reply.status = data.status
            reply.content = data.content
          }
          pendingReplies.value.delete(replyId)
        }
      }
    } catch (err) {
      console.error('Failed to poll reply status:', err)
    }
  }

  if (pendingReplies.value.size === 0) {
    stopPolling()
  }
}

const sendReply = async () => {
  if (!newReply.value.trim() || sending.value) return

  sending.value = true
  const content = newReply.value.trim()
  const parentId = replyingTo.value?.id

  try {
    const url = parentId
      ? `${API_URL}/api/forum/replies/${parentId}/replies`
      : `${API_URL}/api/forum/threads/${thread.value.id}/replies`

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content })
    })

    if (res.ok) {
      const reply = await res.json()
      thread.value.replies.push(reply)
      newReply.value = ''
      replyingTo.value = null
    }
  } catch (err) {
    console.error('Failed to send reply:', err)
  } finally {
    sending.value = false
  }
}

const cancelReply = () => {
  replyingTo.value = null
  newReply.value = ''
}

const setReplyingTo = (reply) => {
  replyingTo.value = reply
  // Scroll to reply input
  setTimeout(() => {
    document.querySelector('.reply-input')?.scrollIntoView({ behavior: 'smooth' })
  }, 100)
}

const deleteThread = async () => {
  if (!confirm('Are you sure you want to delete this thread?')) return

  try {
    const res = await fetch(`${API_URL}/api/forum/threads/${thread.value.id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      router.push({ name: 'forum' })
    }
  } catch (err) {
    console.error('Failed to delete thread:', err)
  }
}

const deleteReply = async (replyId) => {
  if (!confirm('Are you sure you want to delete this reply?')) return

  try {
    const res = await fetch(`${API_URL}/api/forum/replies/${replyId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      thread.value.replies = thread.value.replies.filter(r => r.id !== replyId)
    }
  } catch (err) {
    console.error('Failed to delete reply:', err)
  }
}

const canDelete = (item) => {
  return item.user?.id === authStore.user?.id || authStore.user?.is_admin
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return mins <= 1 ? 'just now' : `${mins}m ago`
  }
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}h ago`
  }
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}d ago`
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// Build reply tree for nested display
const replyTree = computed(() => {
  if (!thread.value?.replies) return []

  const replies = thread.value.replies
  const rootReplies = replies.filter(r => !r.parent_id)
  const childrenMap = {}

  replies.forEach(r => {
    if (r.parent_id) {
      if (!childrenMap[r.parent_id]) {
        childrenMap[r.parent_id] = []
      }
      childrenMap[r.parent_id].push(r)
    }
  })

  const buildTree = (reply, depth = 0) => {
    const children = childrenMap[reply.id] || []
    return {
      ...reply,
      depth,
      children: children.map(c => buildTree(c, depth + 1))
    }
  }

  return rootReplies.map(r => buildTree(r, 0))
})


onMounted(() => {
  fetchThread()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <AppHeader @donate="showDonateToast = true" />

    <main class="max-w-4xl mx-auto px-4 py-6">
      <!-- Loading -->
      <div v-if="loading" class="text-center py-12">
        <p class="text-gray-500 text-sm">Loading thread...</p>
      </div>

      <div v-else-if="thread">
        <!-- Back button -->
        <router-link
          to="/forum"
          class="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 mb-4 transition-colors"
        >
          <span>←</span>
          <span>Back to Forum</span>
        </router-link>

        <!-- Thread header -->
        <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-5 mb-4">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <div v-if="thread.is_pinned" class="mb-2">
                <span class="text-[10px] text-purple-400 font-medium">PINNED</span>
              </div>
              <h1 class="text-lg font-semibold text-gray-100">{{ thread.title }}</h1>
              <div class="flex items-center gap-2 mt-2 text-xs text-gray-500">
                <span>{{ thread.user?.name || 'Anonymous' }}</span>
                <span class="text-gray-700">·</span>
                <span>{{ formatDate(thread.created_at) }}</span>
              </div>
            </div>
            <button
              v-if="canDelete(thread)"
              @click="deleteThread"
              class="text-xs text-gray-600 hover:text-red-400 transition-colors"
            >
              Delete
            </button>
          </div>

          <div class="mt-4 text-sm text-gray-300 markdown-content" v-html="renderMarkdown(thread.content)"></div>
        </div>

        <!-- Replies section -->
        <div class="mb-4">
          <h2 class="text-sm font-medium text-gray-400 mb-3">
            {{ thread.replies?.length || 0 }} {{ thread.replies?.length === 1 ? 'Reply' : 'Replies' }}
          </h2>

          <!-- Reply list (flat with indentation) -->
          <div class="space-y-3">
            <template v-for="reply in replyTree" :key="reply.id">
              <!-- Root reply -->
              <div class="border rounded-lg p-4 transition-colors bg-gray-800/30 border-gray-700/50">
                <!-- Header -->
                <div class="flex items-start justify-between gap-3">
                  <div class="flex items-center gap-2">
                    <div class="w-6 h-6 rounded-full bg-gray-700 flex items-center justify-center">
                      <span class="text-[10px] text-gray-400">
                        {{ getDisplayName(reply)[0].toUpperCase() }}
                      </span>
                    </div>
                    <span class="text-sm text-gray-300">{{ getDisplayName(reply) }}</span>
                    <span class="text-xs text-gray-600">{{ formatDate(reply.created_at) }}</span>
                  </div>

                  <div class="flex items-center gap-2">
                    <button
                      @click="setReplyingTo(reply)"
                      class="text-[11px] text-gray-600 hover:text-purple-400 transition-colors"
                    >
                      Reply
                    </button>
                    <button
                      v-if="canDelete(reply)"
                      @click="deleteReply(reply.id)"
                      class="text-[11px] text-gray-600 hover:text-red-400 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                <!-- Content -->
                <div class="mt-2">
                  <!-- Pending state -->
                  <div v-if="reply.status === 'pending' || reply.status === 'processing'" class="text-gray-500 text-sm">
                    <span class="inline-flex items-center gap-2">
                      <span class="animate-pulse">●</span>
                      {{ getDisplayName(reply) }} is typing...
                    </span>
                  </div>
                  <!-- Failed state -->
                  <div v-else-if="reply.status === 'failed'" class="text-red-400 text-sm">
                    Failed to load message
                  </div>
                  <!-- Content -->
                  <div v-else class="text-sm text-gray-300 markdown-content" v-html="renderMarkdown(reply.content)"></div>
                </div>
              </div>

              <!-- Nested replies (children) -->
              <template v-for="child in reply.children" :key="child.id">
                <div class="ml-6 border rounded-lg p-4 transition-colors bg-gray-800/30 border-gray-700/50">
                  <!-- Header -->
                  <div class="flex items-start justify-between gap-3">
                    <div class="flex items-center gap-2">
                      <div class="w-6 h-6 rounded-full bg-gray-700 flex items-center justify-center">
                        <span class="text-[10px] text-gray-400">
                          {{ getDisplayName(child)[0].toUpperCase() }}
                        </span>
                      </div>
                      <span class="text-sm text-gray-300">{{ getDisplayName(child) }}</span>
                      <span class="text-xs text-gray-600">{{ formatDate(child.created_at) }}</span>
                    </div>

                    <div class="flex items-center gap-2">
                      <button
                        @click="setReplyingTo(child)"
                        class="text-[11px] text-gray-600 hover:text-purple-400 transition-colors"
                      >
                        Reply
                      </button>
                      <button
                        v-if="canDelete(child)"
                        @click="deleteReply(child.id)"
                        class="text-[11px] text-gray-600 hover:text-red-400 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <!-- Content -->
                  <div class="mt-2">
                    <div v-if="child.status === 'pending' || child.status === 'processing'" class="text-gray-500 text-sm">
                      <span class="inline-flex items-center gap-2">
                        <span class="animate-pulse">●</span>
                        {{ getDisplayName(child) }} is typing...
                      </span>
                    </div>
                    <div v-else-if="child.status === 'failed'" class="text-red-400 text-sm">
                      Failed to load message
                    </div>
                    <div v-else class="text-sm text-gray-300 markdown-content" v-html="renderMarkdown(child.content)"></div>
                  </div>
                </div>

                <!-- Second level nested replies -->
                <template v-for="grandchild in child.children" :key="grandchild.id">
                  <div class="ml-12 border rounded-lg p-4 transition-colors bg-gray-800/30 border-gray-700/50">
                    <div class="flex items-start justify-between gap-3">
                      <div class="flex items-center gap-2">
                        <div class="w-6 h-6 rounded-full bg-gray-700 flex items-center justify-center">
                          <span class="text-[10px] text-gray-400">
                            {{ getDisplayName(grandchild)[0].toUpperCase() }}
                          </span>
                        </div>
                        <span class="text-sm text-gray-300">{{ getDisplayName(grandchild) }}</span>
                        <span class="text-xs text-gray-600">{{ formatDate(grandchild.created_at) }}</span>
                      </div>
                      <div class="flex items-center gap-2">
                        <button
                          @click="setReplyingTo(grandchild)"
                          class="text-[11px] text-gray-600 hover:text-purple-400 transition-colors"
                        >
                          Reply
                        </button>
                        <button
                          v-if="canDelete(grandchild)"
                          @click="deleteReply(grandchild.id)"
                          class="text-[11px] text-gray-600 hover:text-red-400 transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <div class="mt-2">
                      <div v-if="grandchild.status === 'pending' || grandchild.status === 'processing'" class="text-gray-500 text-sm">
                        <span class="inline-flex items-center gap-2">
                          <span class="animate-pulse">●</span>
                          {{ getDisplayName(grandchild) }} is typing...
                        </span>
                      </div>
                      <div v-else-if="grandchild.status === 'failed'" class="text-red-400 text-sm">
                        Failed to load message
                      </div>
                      <div v-else class="text-sm text-gray-300 markdown-content" v-html="renderMarkdown(grandchild.content)"></div>
                    </div>
                  </div>
                </template>
              </template>
            </template>
          </div>

          <!-- Empty replies -->
          <div v-if="!thread.replies?.length" class="text-center py-8">
            <p class="text-gray-600 text-sm">No replies yet. Be the first to respond!</p>
          </div>
        </div>

        <!-- Reply input -->
        <div class="reply-input bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
          <div v-if="replyingTo" class="mb-3 p-2 bg-gray-900/50 rounded text-xs">
            <div class="flex items-center justify-between">
              <span class="text-gray-500">
                Replying to
                <span class="text-gray-300">
                  {{ replyingTo.agent?.display_name || replyingTo.user?.name || 'Anonymous' }}
                </span>
              </span>
              <button @click="cancelReply" class="text-gray-600 hover:text-gray-400">
                ✕
              </button>
            </div>
          </div>

          <textarea
            v-model="newReply"
            rows="3"
            maxlength="5000"
            placeholder="Write a reply..."
            class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500 resize-none"
          ></textarea>

          <div class="flex justify-end mt-3">
            <button
              @click="sendReply"
              :disabled="!newReply.trim() || sending"
              class="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs rounded transition-colors"
            >
              {{ sending ? 'Sending...' : 'Send Reply' }}
            </button>
          </div>
        </div>
      </div>
    </main>

    <DonateToast
      v-if="showDonateToast"
      @close="showDonateToast = false"
      @donate="showDonateToast = false"
    />
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
</style>
