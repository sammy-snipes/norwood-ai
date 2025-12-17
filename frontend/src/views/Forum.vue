<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppHeader from '../components/AppHeader.vue'
import DonateToast from '../components/DonateToast.vue'

const router = useRouter()
const authStore = useAuthStore()

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const threads = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const newThread = ref({ title: '', content: '' })
const creating = ref(false)
const showDonateToast = ref(false)

// Pagination
const page = ref(1)
const perPage = ref(20)
const total = ref(0)

const fetchThreads = async () => {
  loading.value = true
  try {
    const res = await fetch(`${API_URL}/api/forum/threads?page=${page.value}&per_page=${perPage.value}`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      threads.value = data.threads
      total.value = data.total
    }
  } catch (err) {
    console.error('Failed to fetch threads:', err)
  } finally {
    loading.value = false
  }
}

const createThread = async () => {
  if (!newThread.value.title.trim() || !newThread.value.content.trim() || creating.value) return

  creating.value = true
  try {
    const res = await fetch(`${API_URL}/api/forum/threads`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        title: newThread.value.title.trim(),
        content: newThread.value.content.trim()
      })
    })
    if (res.ok) {
      const thread = await res.json()
      showCreateModal.value = false
      newThread.value = { title: '', content: '' }
      // Navigate to the new thread
      router.push({ name: 'forum-thread', params: { threadId: thread.id } })
    }
  } catch (err) {
    console.error('Failed to create thread:', err)
  } finally {
    creating.value = false
  }
}

const goToThread = (threadId) => {
  router.push({ name: 'forum-thread', params: { threadId } })
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  // Less than 1 hour
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return mins <= 1 ? 'just now' : `${mins}m ago`
  }
  // Less than 24 hours
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}h ago`
  }
  // Less than 7 days
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}d ago`
  }
  // Otherwise show date
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const totalPages = () => Math.ceil(total.value / perPage.value)

const nextPage = () => {
  if (page.value < totalPages()) {
    page.value++
    fetchThreads()
  }
}

const prevPage = () => {
  if (page.value > 1) {
    page.value--
    fetchThreads()
  }
}

onMounted(() => {
  fetchThreads()
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <AppHeader @donate="showDonateToast = true" />

    <main class="max-w-4xl mx-auto px-4 py-6">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-xl font-semibold text-gray-100">Forum</h1>
          <p class="text-xs text-gray-500 mt-1">Discuss all things hair loss with the community</p>
        </div>
        <button
          @click="showCreateModal = true"
          class="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded transition-colors"
        >
          + New Thread
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-12">
        <p class="text-gray-500 text-sm">Loading threads...</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="threads.length === 0" class="text-center py-12">
        <p class="text-gray-500 text-sm mb-4">No threads yet. Be the first to start a discussion!</p>
        <button
          @click="showCreateModal = true"
          class="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded transition-colors"
        >
          Create Thread
        </button>
      </div>

      <!-- Thread list -->
      <div v-else class="space-y-2">
        <div
          v-for="thread in threads"
          :key="thread.id"
          @click="goToThread(thread.id)"
          class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 hover:bg-gray-800 hover:border-gray-600 cursor-pointer transition-colors"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <!-- Pinned badge -->
              <div v-if="thread.is_pinned" class="flex items-center gap-1 mb-1">
                <span class="text-[10px] text-purple-400 font-medium">PINNED</span>
              </div>

              <!-- Title -->
              <h3 class="text-sm font-medium text-gray-100 truncate">{{ thread.title }}</h3>

              <!-- Meta -->
              <div class="flex items-center gap-2 mt-1.5 text-[11px] text-gray-500">
                <span>{{ thread.user?.name || 'Anonymous' }}</span>
                <span class="text-gray-700">·</span>
                <span>{{ formatDate(thread.created_at) }}</span>
                <span class="text-gray-700">·</span>
                <span>{{ thread.reply_count }} {{ thread.reply_count === 1 ? 'reply' : 'replies' }}</span>
              </div>
            </div>

            <!-- Activity indicator -->
            <div class="text-right flex-shrink-0">
              <p class="text-[10px] text-gray-600">last activity</p>
              <p class="text-xs text-gray-400">{{ formatDate(thread.last_activity_at) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages() > 1" class="flex items-center justify-center gap-4 mt-6">
        <button
          @click="prevPage"
          :disabled="page === 1"
          class="px-3 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Previous
        </button>
        <span class="text-xs text-gray-500">
          Page {{ page }} of {{ totalPages() }}
        </span>
        <button
          @click="nextPage"
          :disabled="page >= totalPages()"
          class="px-3 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Next
        </button>
      </div>
    </main>

    <!-- Create Thread Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      @click.self="showCreateModal = false"
    >
      <div class="bg-gray-800 border border-gray-700 rounded-lg w-full max-w-lg">
        <div class="p-4 border-b border-gray-700">
          <h2 class="text-sm font-medium text-gray-100">Create New Thread</h2>
        </div>

        <div class="p-4 space-y-4">
          <div>
            <label class="block text-xs text-gray-400 mb-1.5">Title</label>
            <input
              v-model="newThread.title"
              type="text"
              maxlength="255"
              placeholder="What's on your mind?"
              class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div>
            <label class="block text-xs text-gray-400 mb-1.5">Content</label>
            <textarea
              v-model="newThread.content"
              rows="5"
              maxlength="10000"
              placeholder="Share your thoughts, questions, or experiences..."
              class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500 resize-none"
            ></textarea>
          </div>
        </div>

        <div class="p-4 border-t border-gray-700 flex justify-end gap-3">
          <button
            @click="showCreateModal = false"
            class="px-4 py-2 text-xs text-gray-400 hover:text-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            @click="createThread"
            :disabled="!newThread.title.trim() || !newThread.content.trim() || creating"
            class="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs rounded transition-colors"
          >
            {{ creating ? 'Creating...' : 'Create Thread' }}
          </button>
        </div>
      </div>
    </div>

    <DonateToast
      v-if="showDonateToast"
      @close="showDonateToast = false"
      @donate="showDonateToast = false"
    />
  </div>
</template>
