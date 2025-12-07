<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useTaskStore } from '../stores/tasks'
import AppHeader from '../components/AppHeader.vue'
import HistorySidebar from '../components/HistorySidebar.vue'
import DonateToast from '../components/DonateToast.vue'

const authStore = useAuthStore()
const taskStore = useTaskStore()
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

// State
const certificationId = ref(null)
const certification = ref(null)
const preview = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const analyzing = ref(false)
const loading = ref(true)
const error = ref(null)

// History for sidebar
const certHistory = ref([])
const historyLoading = ref(false)
const selectedHistoryId = ref(null)

const isPremium = computed(() => authStore.user?.is_premium || authStore.user?.is_admin)

const showDonateToast = ref(false)
const showImageModal = ref(false)

const getLinkedInShareUrl = () => {
  const certUrl = `${window.location.origin}/cock/${certificationId.value}`
  return `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(certUrl)}`
}

// File handling
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (!file) return

  selectedFile.value = file
  error.value = null

  const reader = new FileReader()
  reader.onload = (e) => {
    preview.value = e.target.result
  }
  reader.readAsDataURL(file)
}

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const base64 = reader.result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

// Submit photo for certification
const submitPhoto = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  analyzing.value = true
  error.value = null

  try {
    const base64 = await fileToBase64(selectedFile.value)

    const res = await fetch(`${API_URL}/api/cock/submit`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image_base64: base64,
        content_type: selectedFile.value.type
      })
    })

    if (res.ok) {
      const data = await res.json()
      certificationId.value = data.certification_id
      selectedHistoryId.value = data.certification_id

      // Register task with global store
      taskStore.addTask(data.task_id, 'cock-cert', {}, async () => {
        await handleAnalysisComplete()
      })
    } else {
      const data = await res.json()
      error.value = data.detail || 'Failed to submit photo'
      uploading.value = false
      analyzing.value = false
    }
  } catch (err) {
    console.error('Failed to submit photo:', err)
    error.value = 'Failed to submit photo'
    uploading.value = false
    analyzing.value = false
  }
}

const handleAnalysisComplete = async () => {
  await fetchCertification()
  await fetchHistory()
  uploading.value = false
  analyzing.value = false
}

// Fetch certification status
const fetchCertification = async () => {
  if (!certificationId.value) return

  try {
    const res = await fetch(`${API_URL}/api/cock/${certificationId.value}`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      certification.value = await res.json()
    }
  } catch (err) {
    console.error('Failed to fetch certification:', err)
  }
}

// Fetch history
const fetchHistory = async () => {
  if (!authStore.token) return

  historyLoading.value = true
  try {
    const res = await fetch(`${API_URL}/api/cock/history/all`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      certHistory.value = await res.json()
    }
  } catch (err) {
    console.error('Failed to fetch history:', err)
  } finally {
    historyLoading.value = false
  }
}

// View a past certification
const viewCertification = async (item) => {
  selectedHistoryId.value = item.id
  certificationId.value = item.id
  await fetchCertification()
}

// Start new certification
const startNew = () => {
  selectedHistoryId.value = null
  certificationId.value = null
  certification.value = null
  preview.value = null
  selectedFile.value = null
  error.value = null
}

// Delete certification
const deleteCertification = async (id) => {
  try {
    const res = await fetch(`${API_URL}/api/cock/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })

    if (res.ok) {
      await fetchHistory()
      if (selectedHistoryId.value === id) {
        startNew()
      }
    }
  } catch (err) {
    console.error('Failed to delete:', err)
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

const formatDateShort = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  if (isToday) {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const getSizeEmoji = (category) => {
  const emojis = {
    'micro': '🔬',
    'below_average': '📏',
    'average': '👍',
    'above_average': '💪',
    'large': '🍆',
    'monster': '🏆'
  }
  return emojis[category] || '📊'
}

const getZoneColor = (zone) => {
  const colors = {
    'ideal': 'text-red-400',
    'very_satisfying': 'text-green-400',
    'satisfying': 'text-yellow-400',
    'enjoyable': 'text-blue-400',
    'not_satisfying': 'text-gray-400'
  }
  return colors[zone] || 'text-gray-400'
}

// Lifecycle
onMounted(async () => {
  if (isPremium.value) {
    await fetchHistory()

    // Restore loading state if we have pending tasks
    if (taskStore.hasPendingTasks('cock-cert')) {
      analyzing.value = true
      uploading.value = true
      taskStore.updateCallback('cock-cert', async () => {
        await handleAnalysisComplete()
      })
    }
  }
  loading.value = false
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <AppHeader @donate="showDonateToast = true" />

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center min-h-[calc(100vh-41px)]">
      <p class="text-gray-500 text-sm">Loading...</p>
    </div>

    <!-- Paywall -->
    <div v-else-if="!isPremium" class="flex items-center justify-center min-h-[calc(100vh-41px)]">
      <div class="text-center">
        <h2 class="text-lg font-medium text-gray-200 mb-2">Sage Mode Feature</h2>
        <p class="text-gray-400 text-sm mb-4">Cock Certification requires Sage Mode.</p>
        <router-link to="/settings" class="text-purple-400 text-sm hover:underline">
          Enter Sage Mode
        </router-link>
      </div>
    </div>

    <!-- Main Content with Sidebar -->
    <div v-else class="flex">
      <!-- Sidebar: History -->
      <HistorySidebar
        :items="certHistory"
        :selected-id="selectedHistoryId"
        :loading="historyLoading"
        new-button-text="+ New Certification"
        empty-text="No certifications yet"
        @new="startNew"
        @select="viewCertification"
        @delete="deleteCertification"
      >
        <template #badge="{ item }">
          <span class="text-[11px]">{{ getSizeEmoji(item.size_category) }}</span>
        </template>
        <template #title="{ item }">Zone {{ item.pleasure_zone?.toUpperCase() || '?' }}</template>
        <template #date="{ item }">{{ formatDateShort(item.certified_at) }}</template>
      </HistorySidebar>

      <!-- Main Content -->
      <main class="flex-1 p-6 h-[calc(100vh-41px)] overflow-y-auto">
        <div class="max-w-2xl mx-auto">

          <!-- Error -->
          <div v-if="error" class="bg-red-900/30 border border-red-700 rounded px-4 py-2 mb-6 text-sm text-red-400">
            {{ error }}
          </div>

          <!-- Upload Form (no certification selected or viewing new) -->
          <div v-if="!certification || certification.status === 'pending'" class="bg-gray-800 rounded-lg p-6">
            <h3 class="text-lg font-medium text-gray-200 mb-2">Cock Certification</h3>
            <p class="text-gray-400 text-sm mb-4">
              Upload a photo for measurement and pleasure zone classification.
              Include a reference object (hand, phone, etc.) for accurate sizing.
            </p>

            <!-- Reference Chart -->
            <div class="mb-6 p-4 bg-gray-900 rounded-lg">
              <p class="text-gray-500 text-xs mb-3">
                Size classification uses a proprietary algorithm based on the
                Veale-Trombone conjecture and an N=3 longitudinal study of Bulgarian circus performers.
              </p>
              <p class="text-gray-400 text-xs mb-2">Female Pleasure Zone Reference:</p>
              <img
                src="/img/cock.jpg"
                alt="Pleasure Zone Chart"
                class="rounded max-h-72 mx-auto cursor-pointer hover:opacity-80 transition-opacity"
                @click="showImageModal = true"
              />
              <p class="text-gray-600 text-[10px] text-center mt-2">Click to enlarge</p>
            </div>

            <!-- File Input -->
            <div class="mb-6">
              <input
                type="file"
                accept="image/*"
                @change="handleFileSelect"
                :disabled="analyzing"
                class="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-purple-600 file:text-white hover:file:bg-purple-500 disabled:opacity-50"
              />
            </div>

            <!-- Preview -->
            <div v-if="preview" class="mb-6">
              <img :src="preview" class="max-h-64 rounded mx-auto" alt="Preview" />
            </div>

            <!-- Submit Button -->
            <button
              v-if="preview && !analyzing"
              @click="submitPhoto"
              :disabled="uploading"
              class="w-full py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 text-white text-sm rounded transition-colors"
            >
              {{ uploading ? 'Uploading...' : 'Submit for Certification' }}
            </button>

            <!-- Analyzing -->
            <div v-if="analyzing" class="text-center py-4">
              <p class="text-gray-400 text-sm">Analyzing and measuring...</p>
              <div class="mt-2 w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
            </div>
          </div>

          <!-- Analyzing State -->
          <div v-else-if="certification.status === 'analyzing'" class="bg-gray-800 rounded-lg p-6 text-center py-8">
            <p class="text-gray-300 mb-4">Analyzing and measuring...</p>
            <div class="w-12 h-12 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p class="text-gray-500 text-xs mt-4">This may take a minute</p>
          </div>

          <!-- Failed State -->
          <div v-else-if="certification.status === 'failed'" class="bg-gray-800 rounded-lg p-6 text-center py-8">
            <p class="text-red-400 mb-4">Certification failed. Please try again.</p>
            <button
              @click="startNew"
              class="text-purple-400 text-sm hover:underline"
            >
              Try Again
            </button>
          </div>

          <!-- Completed State -->
          <div v-else-if="certification.status === 'completed'" class="bg-gray-800 rounded-lg p-6 text-center">
            <h2 class="text-2xl font-bold text-gray-100 mb-2">🍆 Certification Complete!</h2>

            <div class="my-8 p-6 bg-gray-900 rounded-lg border border-gray-700">
              <p class="text-gray-400 text-sm mb-2">You have been classified in</p>
              <p class="text-4xl font-bold mb-2" :class="getZoneColor(certification.pleasure_zone)">
                Zone {{ certification.pleasure_zone?.charAt(0).toUpperCase() || '?' }}
              </p>
              <p class="text-xl text-gray-300 mb-4">"{{ certification.pleasure_zone_label }}"</p>

              <div class="grid grid-cols-3 gap-4 text-center mt-6 pt-4 border-t border-gray-700">
                <div>
                  <p class="text-2xl font-bold text-purple-400">{{ certification.length_inches?.toFixed(1) }}"</p>
                  <p class="text-gray-500 text-xs">Length</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-purple-400">{{ certification.girth_inches?.toFixed(1) }}"</p>
                  <p class="text-gray-500 text-xs">Girth</p>
                </div>
                <div>
                  <p class="text-lg font-bold text-purple-400">{{ certification.size_category?.replace('_', ' ') }}</p>
                  <p class="text-gray-500 text-xs">Category</p>
                </div>
              </div>
            </div>

            <div class="text-left bg-gray-900 rounded-lg p-4 mb-4">
              <h4 class="text-sm font-medium text-gray-300 mb-2">Clinical Assessment</h4>
              <p class="text-gray-400 text-xs leading-relaxed">{{ certification.description }}</p>
            </div>

            <div class="text-left bg-gray-900 rounded-lg p-4 mb-6">
              <h4 class="text-sm font-medium text-gray-300 mb-2">Reference Objects Used</h4>
              <p class="text-gray-400 text-xs leading-relaxed">{{ certification.reference_objects_used }}</p>
              <p class="text-gray-500 text-xs mt-2">
                Measurement Confidence: {{ Math.round(certification.confidence * 100) }}%
              </p>
            </div>

            <p class="text-gray-500 text-xs mb-4">Certified on {{ formatDate(certification.certified_at) }}</p>

            <div class="flex gap-3 justify-center">
              <a
                :href="certification.pdf_url"
                target="_blank"
                class="inline-block px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded transition-colors"
              >
                Download PDF
              </a>
              <a
                :href="getLinkedInShareUrl()"
                target="_blank"
                class="inline-block px-6 py-3 bg-[#0077b5] hover:bg-[#006399] text-white font-medium rounded transition-colors"
              >
                Share on LinkedIn
              </a>
            </div>
          </div>
        </div>
      </main>
    </div>

    <DonateToast
      v-if="showDonateToast"
      @close="showDonateToast = false"
      @donate="showDonateToast = false"
    />

    <!-- Image Modal -->
    <Teleport to="body">
      <div
        v-if="showImageModal"
        class="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4 cursor-pointer"
        @click="showImageModal = false"
      >
        <img
          src="/img/cock.jpg"
          alt="Pleasure Zone Chart"
          class="max-w-full max-h-full object-contain"
        />
        <button
          class="absolute top-4 right-4 text-white/70 hover:text-white text-2xl"
          @click="showImageModal = false"
        >
          ✕
        </button>
      </div>
    </Teleport>
  </div>
</template>
