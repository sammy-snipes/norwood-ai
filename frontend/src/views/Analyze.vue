<script setup>
import { ref } from 'vue'
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

      taskStatus.value = data.status

      if (data.ready) {
        if (data.status === 'completed' && data.result?.success) {
          return { success: true, analysis: data.result.analysis }
        } else {
          return { success: false, error: data.error || 'Analysis failed' }
        }
      }

      await new Promise(resolve => setTimeout(resolve, 1000))
      attempts++
    } catch (err) {
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

    if (pollResult.success) {
      result.value = pollResult.analysis
    } else {
      error.value = pollResult.error
    }
  } catch (err) {
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
}

const getStageColor = (stage) => {
  const stageNum = parseInt(stage)
  if (stageNum <= 2) return 'text-green-400'
  if (stageNum <= 4) return 'text-yellow-400'
  return 'text-red-400'
}
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <!-- Header -->
    <header class="border-b border-gray-800 px-6 py-4">
      <div class="max-w-6xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-8">
          <router-link to="/analyze" class="flex items-center gap-2">
            <span class="font-bold text-xl">Norwood AI</span>
          </router-link>
          <nav class="flex gap-6">
            <router-link to="/analyze" class="text-sm text-white transition-colors">
              Analyze
            </router-link>
            <router-link to="/settings" class="text-sm text-gray-500 hover:text-gray-300 transition-colors">
              Settings
            </router-link>
          </nav>
        </div>
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2">
            <img
              v-if="authStore.user?.avatar_url"
              :src="authStore.user.avatar_url"
              class="w-8 h-8 rounded-full"
            />
            <span class="text-gray-400 text-sm">{{ authStore.user?.name }}</span>
          </div>
          <button
            @click="handleLogout"
            class="text-gray-500 hover:text-gray-300 text-sm"
          >
            Logout
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="p-8">
      <div class="max-w-2xl mx-auto">
        <!-- Free tier notice -->
        <div
          v-if="!authStore.user?.is_premium && authStore.user?.free_analyses_remaining > 0"
          class="mb-6 p-4 bg-blue-900/30 border border-blue-700 rounded-lg text-center"
        >
          <p class="text-blue-300">
            You have <span class="font-bold">{{ authStore.user?.free_analyses_remaining }}</span> free analysis remaining
          </p>
        </div>

        <div
          v-if="!authStore.user?.is_premium && authStore.user?.free_analyses_remaining === 0"
          class="mb-6 p-4 bg-orange-900/30 border border-orange-700 rounded-lg text-center"
        >
          <p class="text-orange-300 mb-2">You've used your free analysis!</p>
          <button class="px-4 py-2 bg-orange-600 hover:bg-orange-500 rounded-lg font-semibold">
            Upgrade to Premium - $5
          </button>
        </div>

        <!-- Upload Area -->
        <div
          v-if="!previewUrl"
          @drop.prevent="onDrop"
          @dragover.prevent
          class="border-2 border-dashed border-gray-600 rounded-lg p-12 text-center hover:border-gray-500 transition-colors cursor-pointer"
          @click="$refs.fileInput.click()"
        >
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="onFileSelect"
          />
          <div class="text-gray-400">
            <svg class="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="text-lg">Drop an image here or click to upload</p>
            <p class="text-sm mt-2">JPEG, PNG, GIF, or WebP up to 10MB</p>
          </div>
        </div>

        <!-- Preview & Analyze -->
        <div v-else class="space-y-6">
          <div class="relative">
            <img
              :src="previewUrl"
              alt="Preview"
              class="w-full max-h-96 object-contain rounded-lg bg-gray-800"
            />
            <button
              @click="reset"
              class="absolute top-2 right-2 bg-gray-800 hover:bg-gray-700 rounded-full p-2"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <button
            @click="analyze"
            :disabled="isLoading || (!authStore.user?.is_premium && authStore.user?.free_analyses_remaining === 0)"
            class="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors"
          >
            <span v-if="isLoading" class="flex items-center justify-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ taskStatus === 'submitting' ? 'Submitting...' : taskStatus === 'started' ? 'Processing...' : 'Analyzing...' }}
            </span>
            <span v-else>🔥 Destroy Me 🔥</span>
          </button>
        </div>

        <!-- Error -->
        <div v-if="error" class="mt-6 p-4 bg-red-900/50 border border-red-700 rounded-lg">
          <p class="text-red-400">{{ error }}</p>
        </div>

        <!-- Results -->
        <div v-if="result" class="mt-6 space-y-4">
          <!-- Stage Display -->
          <div class="p-6 bg-gray-800 rounded-lg text-center">
            <p class="text-gray-400 text-sm uppercase tracking-wide">Norwood Stage</p>
            <p :class="['text-7xl font-black', getStageColor(result.stage)]">
              {{ result.stage }}
            </p>
            <p class="text-gray-400 mt-2 text-lg">{{ result.description }}</p>
          </div>

          <!-- THE VERDICT -->
          <div class="p-6 bg-gradient-to-br from-red-900/50 to-orange-900/50 border-2 border-red-600 rounded-lg">
            <p class="text-red-400 text-sm uppercase tracking-wide mb-3">THE VERDICT</p>
            <p class="text-xl text-white leading-relaxed font-medium">{{ result.roast }}</p>
          </div>

          <!-- Technical Details -->
          <details class="bg-gray-800/50 rounded-lg">
            <summary class="p-4 cursor-pointer text-gray-400 hover:text-gray-300">
              Technical Analysis
            </summary>
            <div class="px-4 pb-4 text-gray-400 text-sm">
              <p><span class="text-gray-500">Confidence:</span> {{ result.confidence }}</p>
              <p class="mt-2"><span class="text-gray-500">Reasoning:</span> {{ result.reasoning }}</p>
            </div>
          </details>

          <!-- Try Again -->
          <button
            @click="reset"
            class="w-full py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-semibold transition-colors"
          >
            Try Another Photo
          </button>
        </div>
      </div>
    </main>
  </div>
</template>
