<script setup>
import { ref } from 'vue'

// Use relative URLs in production (served by FastAPI), absolute in dev
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const selectedFile = ref(null)
const previewUrl = ref(null)
const isLoading = ref(false)
const result = ref(null)
const error = ref(null)

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

const taskStatus = ref(null)

const pollForResult = async (taskId) => {
  const maxAttempts = 60 // 60 seconds max
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      const response = await fetch(`${API_URL}/tasks/${taskId}`)
      const data = await response.json()

      console.log('[DEBUG] Poll response:', data)
      taskStatus.value = data.status

      if (data.ready) {
        if (data.status === 'completed' && data.result?.success) {
          return { success: true, analysis: data.result.analysis }
        } else {
          return { success: false, error: data.error || 'Analysis failed' }
        }
      }

      // Wait 1 second before next poll
      await new Promise(resolve => setTimeout(resolve, 1000))
      attempts++
    } catch (err) {
      console.error('[DEBUG] Poll error:', err)
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

    console.log('[DEBUG] Submitting task to:', `${API_URL}/analyze`)

    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      body: formData,
    })

    const data = await response.json()
    console.log('[DEBUG] Submit response:', data)

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to submit')
    }

    // Poll for result
    taskStatus.value = 'processing'
    const pollResult = await pollForResult(data.task_id)

    if (pollResult.success) {
      result.value = pollResult.analysis
    } else {
      error.value = pollResult.error
    }
  } catch (err) {
    console.error('[DEBUG] Error:', err)
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
  <div class="min-h-screen bg-gray-900 text-white p-8">
    <div class="max-w-2xl mx-auto">
      <h1 class="text-4xl font-bold text-center mb-2">Norwood AI</h1>
      <p class="text-gray-400 text-center mb-8">Upload a photo and get absolutely destroyed</p>

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
          :disabled="isLoading"
          class="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors"
        >
          <span v-if="isLoading" class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ taskStatus === 'submitting' ? 'Submitting...' : taskStatus === 'started' ? 'Processing...' : 'Waiting for worker...' }}
          </span>
          <span v-else>Destroy Me</span>
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

        <!-- THE ROAST -->
        <div class="p-6 bg-gradient-to-br from-red-900/50 to-orange-900/50 border-2 border-red-600 rounded-lg">
          <p class="text-red-400 text-sm uppercase tracking-wide mb-3 flex items-center justify-center gap-2">
            <span>🔥</span> THE VERDICT <span>🔥</span>
          </p>
          <p class="text-xl text-white leading-relaxed font-medium">{{ result.roast }}</p>
        </div>

        <!-- Technical Details (collapsed) -->
        <details class="bg-gray-800/50 rounded-lg">
          <summary class="p-4 cursor-pointer text-gray-400 hover:text-gray-300">
            Technical Analysis
          </summary>
          <div class="px-4 pb-4 text-gray-400 text-sm">
            <p><span class="text-gray-500">Confidence:</span> {{ result.confidence }}</p>
            <p class="mt-2"><span class="text-gray-500">Reasoning:</span> {{ result.reasoning }}</p>
          </div>
        </details>
      </div>
    </div>
  </div>
</template>
