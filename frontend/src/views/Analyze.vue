<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const handleLogout = () => {
  authStore.logout()
  router.push('/')
}

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const selectedFile = ref(null)
const previewUrl = ref(null)
const isLoading = ref(false)
const result = ref(null)
const error = ref(null)
const taskStatus = ref(null)
const selectedHistoryId = ref(null)

// Analysis history for sidebar
const analysisHistory = ref([])
const historyLoading = ref(false)

// Computed: user has unlimited analyses (admin or premium)
const hasUnlimited = computed(() => {
  return authStore.user?.is_admin || authStore.user?.is_premium
})

// Computed: user can analyze
const canAnalyze = computed(() => {
  return hasUnlimited.value || (authStore.user?.free_analyses_remaining > 0)
})

// Fetch analysis history
const fetchHistory = async () => {
  if (!authStore.token) return

  historyLoading.value = true
  try {
    const response = await fetch(`${API_URL}/api/analyses`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (response.ok) {
      analysisHistory.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to fetch history:', err)
  } finally {
    historyLoading.value = false
  }
}

// View a past analysis from history
const viewAnalysis = (item) => {
  selectedHistoryId.value = item.id
  result.value = {
    stage: item.norwood_stage.toString(),
    confidence: item.confidence,
    title: item.title,
    analysis_text: item.analysis_text,
    reasoning: item.reasoning,
    description: `Stage ${item.norwood_stage}`
  }
  // Clear upload state when viewing history
  selectedFile.value = null
  previewUrl.value = null
  error.value = null
}

onMounted(() => {
  fetchHistory()
})

const onFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
    previewUrl.value = URL.createObjectURL(file)
    result.value = null
    error.value = null
  }
}

const onDrop = (event) => {
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) {
    selectedFile.value = file
    previewUrl.value = URL.createObjectURL(file)
    result.value = null
    error.value = null
  }
}

const pollForResult = async (taskId) => {
  const maxAttempts = 60
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      const response = await fetch(`${API_URL}/tasks/${taskId}`)
      const data = await response.json()
      console.log('Poll response:', data)

      taskStatus.value = data.status

      if (data.ready) {
        console.log('Task ready, result:', data.result)
        if (data.result?.success && data.result?.analysis) {
          return { success: true, analysis: data.result.analysis }
        } else {
          return { success: false, error: data.error || data.result?.error || 'Analysis failed' }
        }
      }

      await new Promise(resolve => setTimeout(resolve, 1000))
      attempts++
    } catch (err) {
      console.error('Poll error:', err)
      return { success: false, error: 'Failed to check task status' }
    }
  }

  return { success: false, error: 'Analysis timed out' }
}

const analyze = async () => {
  if (!selectedFile.value) return

  isLoading.value = true
  error.value = null
  result.value = null
  taskStatus.value = 'submitting'

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      },
      body: formData,
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to submit')
    }

    taskStatus.value = 'processing'
    const pollResult = await pollForResult(data.task_id)
    console.log('pollResult:', JSON.stringify(pollResult, null, 2))

    if (pollResult.success && pollResult.analysis) {
      console.log('Setting result...')
      // Set result with explicit structure and fallbacks
      const analysis = pollResult.analysis
      result.value = {
        stage: analysis.stage || 'unknown',
        confidence: analysis.confidence || 'low',
        title: analysis.title || 'Analysis Complete',
        description: analysis.description || '',
        reasoning: analysis.reasoning || '',
        analysis_text: analysis.analysis_text || analysis.reflection || analysis.roast || ''
      }
      console.log('Result set:', result.value)
      // Clear the preview since we have results now
      selectedFile.value = null
      previewUrl.value = null
      console.log('Preview cleared, previewUrl:', previewUrl.value, 'result:', !!result.value)
      // Refresh history and select the new analysis
      await fetchHistory()
      if (analysisHistory.value.length > 0) {
        selectedHistoryId.value = analysisHistory.value[0].id
      }
      authStore.fetchUser()
    } else {
      console.log('Poll failed:', pollResult)
      error.value = pollResult.error || 'Analysis failed'
    }
  } catch (err) {
    console.error('Analysis error:', err)
    error.value = err.message || 'Failed to connect to server'
  } finally {
    isLoading.value = false
    taskStatus.value = null
  }
}

const reset = () => {
  selectedFile.value = null
  previewUrl.value = null
  result.value = null
  error.value = null
  selectedHistoryId.value = null
}

const getStageColor = (stage) => {
  const stageNum = parseInt(stage)
  if (stageNum <= 2) return 'text-green-400'
  if (stageNum <= 4) return 'text-yellow-400'
  return 'text-red-400'
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  if (isToday) {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <!-- Header -->
    <header class="border-b border-gray-800 px-4 py-2">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-6">
          <router-link to="/analyze" class="font-medium text-sm">
            Norwood AI
          </router-link>
          <nav class="flex gap-4">
            <router-link to="/analyze" class="text-xs text-gray-400 hover:text-white transition-colors">
              Analyze
            </router-link>
            <router-link to="/settings" class="text-xs text-gray-500 hover:text-gray-300 transition-colors">
              Settings
            </router-link>
          </nav>
        </div>
        <div class="flex items-center gap-3">
          <!-- Tier badge -->
          <span v-if="hasUnlimited" class="text-xs text-purple-400">
            {{ authStore.user?.is_admin ? 'Admin' : 'Premium' }}
          </span>
          <span v-else-if="authStore.user?.free_analyses_remaining > 0" class="text-xs text-gray-500">
            {{ authStore.user?.free_analyses_remaining }} free
          </span>
          <span v-else class="text-xs text-orange-400">
            0 remaining
          </span>
          <div class="flex items-center gap-2">
            <img
              v-if="authStore.user?.avatar_url"
              :src="authStore.user.avatar_url"
              class="w-5 h-5 rounded-full"
            />
            <span class="text-gray-500 text-xs">{{ authStore.user?.name }}</span>
          </div>
          <button
            @click="handleLogout"
            class="text-gray-600 hover:text-gray-400 text-xs"
          >
            Logout
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content with Sidebar -->
    <div class="flex">
      <!-- Sidebar: Analysis History -->
      <aside class="w-64 border-r border-gray-800 min-h-[calc(100vh-41px)] p-3 hidden lg:flex lg:flex-col overflow-y-auto">
        <!-- New Analysis button -->
        <button
          @click="reset"
          class="w-full mb-3 py-2 bg-gray-800 hover:bg-gray-700 rounded text-xs text-gray-300 transition-colors"
        >
          + New Analysis
        </button>

        <h2 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
          History
        </h2>

        <div v-if="historyLoading" class="text-gray-500 text-xs">
          Loading...
        </div>

        <div v-else-if="analysisHistory.length === 0" class="text-gray-500 text-xs">
          No analyses yet
        </div>

        <div v-else class="space-y-1 flex-1">
          <div
            v-for="item in analysisHistory"
            :key="item.id"
            @click="viewAnalysis(item)"
            :class="[
              'px-2 py-1.5 rounded transition-colors cursor-pointer flex items-center gap-2',
              selectedHistoryId === item.id
                ? 'bg-gray-700'
                : 'hover:bg-gray-800/50'
            ]"
          >
            <span :class="['text-sm font-bold w-4', getStageColor(item.norwood_stage)]">{{ item.norwood_stage }}</span>
            <span class="text-xs text-gray-400 truncate flex-1">{{ item.title }}</span>
            <span class="text-xs text-gray-600 whitespace-nowrap">{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="flex-1 p-6">
        <div class="max-w-xl mx-auto">
        <!-- Upload Area -->
        <div
          v-if="!previewUrl && !result"
          @drop.prevent="onDrop"
          @dragover.prevent
          class="border border-dashed border-gray-700 rounded-lg p-8 text-center hover:border-gray-600 transition-colors cursor-pointer"
          @click="$refs.fileInput.click()"
        >
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="onFileSelect"
          />
          <div class="text-gray-500">
            <svg class="w-8 h-8 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="text-sm">Drop image or click to upload</p>
            <p class="text-xs mt-1 text-gray-600">JPEG, PNG, GIF, WebP</p>
          </div>
        </div>

        <!-- Preview & Analyze -->
        <div v-if="previewUrl" class="space-y-4">
          <div class="relative">
            <img
              :src="previewUrl"
              alt="Preview"
              class="w-full max-h-64 object-contain rounded-lg bg-gray-800"
            />
            <button
              @click="reset"
              class="absolute top-2 right-2 bg-gray-800/80 hover:bg-gray-700 rounded-full p-1.5"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <button
            @click="analyze"
            :disabled="isLoading || !canAnalyze"
            class="w-full py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 disabled:cursor-not-allowed rounded text-sm font-medium transition-colors"
          >
            <span v-if="isLoading" class="flex items-center justify-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ taskStatus === 'submitting' ? 'Submitting...' : 'Analyzing...' }}
            </span>
            <span v-else>Analyze Norwood</span>
          </button>
        </div>

        <!-- Error -->
        <div v-if="error" class="mt-4 px-3 py-2 bg-red-900/30 border border-red-800 rounded text-sm">
          <p class="text-red-400">{{ error }}</p>
        </div>

        <!-- Results -->
        <div v-if="result" class="mt-4 space-y-2">
          <!-- Stage + Title -->
          <div class="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg">
            <span :class="['text-3xl font-black', getStageColor(result.stage)]">{{ result.stage }}</span>
            <span class="text-gray-400 text-sm italic">{{ result.title }}</span>
          </div>

          <!-- Analysis -->
          <p class="text-sm text-gray-400 leading-relaxed px-1">{{ result.analysis_text }}</p>

          <!-- Details (collapsed) -->
          <details class="text-xs">
            <summary class="px-1 py-1 cursor-pointer text-gray-600 hover:text-gray-500">
              Details
            </summary>
            <div class="px-1 pt-1 text-gray-600">
              <span>{{ result.confidence }} confidence</span>
              <span class="mx-1">·</span>
              <span>{{ result.reasoning }}</span>
            </div>
          </details>
        </div>
        </div>
      </main>
    </div>
  </div>
</template>
