<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import AppHeader from '../components/AppHeader.vue'
import HistorySidebar from '../components/HistorySidebar.vue'

const authStore = useAuthStore()
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

// State
const step = ref(1) // 1=front, 2=left, 3=right, 4=result
const certificationId = ref(null)
const photos = ref({}) // { front: {...}, left: {...}, right: {...} }
const certification = ref(null)
const preview = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const validating = ref(false)
const validationResult = ref(null)
const generating = ref(false)
const cooldownDays = ref(0)
const loading = ref(true)
const error = ref(null)

// Certification history for sidebar
const certHistory = ref([])
const historyLoading = ref(false)
const selectedHistoryId = ref(null)

// File input ref for manual reset
const fileInputRef = ref(null)

let pollInterval = null

const isPremium = computed(() => authStore.user?.is_premium || authStore.user?.is_admin)

const photoTypes = ['front', 'left', 'right']
const currentPhotoType = computed(() => photoTypes[step.value - 1])

const photoInstructions = {
  front: 'Take a clear photo of your face from the front. Pull your hair back to fully expose your hairline and temples.',
  left: 'Take a clear photo of the left side of your head. Show your left temple and hairline clearly.',
  right: 'Take a clear photo of the right side of your head. Show your right temple and hairline clearly.'
}

const allPhotosApproved = computed(() => {
  return photoTypes.every(type => photos.value[type]?.validation_status === 'approved')
})

const currentPhoto = computed(() => photos.value[currentPhotoType.value])
const currentPhotoApproved = computed(() => currentPhoto.value?.validation_status === 'approved')
const isRedoing = ref(false)

// API Functions
const checkCooldown = async () => {
  try {
    const res = await fetch(`${API_URL}/api/certification/cooldown`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      cooldownDays.value = data.days_remaining
    }
  } catch (err) {
    console.error('Failed to check cooldown:', err)
  }
}

const startCertification = async () => {
  try {
    const res = await fetch(`${API_URL}/api/certification/start`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      certificationId.value = data.certification_id
      await fetchCertificationStatus()
    } else if (res.status === 429) {
      const data = await res.json()
      error.value = data.detail
    }
  } catch (err) {
    console.error('Failed to start certification:', err)
    error.value = 'Failed to start certification'
  }
}

const fetchCertificationStatus = async () => {
  if (!certificationId.value) return

  try {
    const res = await fetch(`${API_URL}/api/certification/${certificationId.value}/status`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      certification.value = data

      // Update photos state
      for (const photo of data.photos) {
        photos.value[photo.photo_type] = photo
      }

      // Determine current step based on status
      if (data.status === 'completed') {
        step.value = 4
      } else if (data.status === 'analyzing') {
        step.value = 4
        startPolling()
      } else {
        // Find first unapproved photo type
        for (let i = 0; i < photoTypes.length; i++) {
          const type = photoTypes[i]
          const photo = photos.value[type]
          if (!photo || photo.validation_status !== 'approved') {
            step.value = i + 1
            break
          }
        }
        // If all approved, go to step 4
        if (allPhotosApproved.value) {
          step.value = 4
        }
      }
    }
  } catch (err) {
    console.error('Failed to fetch status:', err)
  }
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (!file) return

  selectedFile.value = file
  validationResult.value = null

  const reader = new FileReader()
  reader.onload = (e) => {
    preview.value = e.target.result
  }
  reader.readAsDataURL(file)
}

const uploadPhoto = async () => {
  if (!selectedFile.value || !certificationId.value) return

  uploading.value = true
  validating.value = true
  error.value = null

  try {
    // Convert file to base64
    const base64 = await fileToBase64(selectedFile.value)

    const res = await fetch(`${API_URL}/api/certification/${certificationId.value}/photo/${currentPhotoType.value}`, {
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
      // Start polling for validation result (pass current photo type)
      pollPhotoValidation(data.photo_id, data.task_id, currentPhotoType.value)
    } else {
      const data = await res.json()
      error.value = data.detail || 'Failed to upload photo'
      uploading.value = false
      validating.value = false
    }
  } catch (err) {
    console.error('Failed to upload photo:', err)
    error.value = 'Failed to upload photo'
    uploading.value = false
    validating.value = false
  }
}

const pollPhotoValidation = async (photoId, taskId, photoType) => {
  const poll = async () => {
    try {
      const res = await fetch(`${API_URL}/tasks/${taskId}`, {
        headers: { 'Authorization': `Bearer ${authStore.token}` }
      })
      if (res.ok) {
        const data = await res.json()
        if (data.status === 'completed' || data.status === 'failed') {
          const currentStep = step.value
          await fetchCertificationStatus()

          // Get the photo validation result for the photo we just uploaded
          const photo = photos.value[photoType]
          const approved = photo?.validation_status === 'approved'

          uploading.value = false
          validating.value = false

          // Show result
          validationResult.value = {
            approved,
            rejection_reason: photo?.rejection_reason,
            quality_notes: photo?.quality_notes
          }

          // Keep step where it is (override fetchCertificationStatus)
          step.value = currentStep

          if (approved) {
            // Show success briefly, then advance
            setTimeout(() => {
              clearPhotoState()
              if (currentStep < 4) {
                step.value = currentStep + 1
              }
            }, 2000)
          }
          return
        }
      }
      // Keep polling
      setTimeout(poll, 1000)
    } catch (err) {
      console.error('Polling error:', err)
      uploading.value = false
      validating.value = false
    }
  }
  poll()
}

const clearPhotoState = () => {
  preview.value = null
  selectedFile.value = null
  validationResult.value = null
  isRedoing.value = false
}

const retake = () => {
  clearPhotoState()
}

const startRedo = () => {
  isRedoing.value = true
  preview.value = null
  selectedFile.value = null
  validationResult.value = null
}

const cancelRedo = () => {
  isRedoing.value = false
  preview.value = null
  selectedFile.value = null
  validationResult.value = null
}

const nextStep = () => {
  if (step.value < 4) {
    clearPhotoState()
    step.value++
  }
}

const prevStep = () => {
  if (step.value > 1) {
    clearPhotoState()
    step.value--
  }
}

const goToStep = (targetStep) => {
  if (targetStep >= 1 && targetStep <= 4) {
    clearPhotoState()
    step.value = targetStep
  }
}

const generateCertificate = async () => {
  if (!certificationId.value || !allPhotosApproved.value) return

  generating.value = true
  error.value = null

  try {
    const res = await fetch(`${API_URL}/api/certification/${certificationId.value}/diagnose`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })

    if (res.ok) {
      // Start polling for completion
      startPolling()
    } else {
      const data = await res.json()
      error.value = data.detail || 'Failed to generate certificate'
      generating.value = false
    }
  } catch (err) {
    console.error('Failed to generate certificate:', err)
    error.value = 'Failed to generate certificate'
    generating.value = false
  }
}

const startPolling = () => {
  if (pollInterval) return

  pollInterval = setInterval(async () => {
    await fetchCertificationStatus()
    if (certification.value?.status === 'completed' || certification.value?.status === 'failed') {
      stopPolling()
      generating.value = false
      // Refresh history when completed
      if (certification.value?.status === 'completed') {
        await fetchHistory()
        selectedHistoryId.value = certificationId.value
      }
    }
  }, 2000)
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      // Remove the data URL prefix to get just the base64
      const base64 = reader.result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
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

// Fetch certification history
const fetchHistory = async () => {
  if (!authStore.token) return

  historyLoading.value = true
  try {
    const res = await fetch(`${API_URL}/api/certification/history`, {
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
  await fetchCertificationStatus()
  step.value = 4
}

// Start a new certification
const startNew = async () => {
  selectedHistoryId.value = null
  certificationId.value = null
  certification.value = null
  photos.value = {}
  step.value = 1
  clearPhotoState()
  await startCertification()
}

// Restart current certification from beginning
const restartCurrent = async () => {
  if (!certificationId.value) return

  try {
    // Delete the current incomplete certification
    await fetch(`${API_URL}/api/certification/${certificationId.value}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    // Start fresh
    await startNew()
  } catch (err) {
    console.error('Failed to restart:', err)
  }
}

// Delete a certification from history
const deleteCertification = async (id) => {
  try {
    const res = await fetch(`${API_URL}/api/certification/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })

    if (res.ok) {
      // Refresh history
      await fetchHistory()

      // If we deleted the current one, start new
      if (selectedHistoryId.value === id) {
        await startNew()
      }
    }
  } catch (err) {
    console.error('Failed to delete:', err)
  }
}

// Lifecycle
onMounted(async () => {
  if (isPremium.value) {
    await fetchHistory()
    await checkCooldown()
    if (cooldownDays.value === 0) {
      await startCertification()
    }
  }
  loading.value = false
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <AppHeader />

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center min-h-[calc(100vh-41px)]">
      <p class="text-gray-500 text-sm">Loading...</p>
    </div>

    <!-- Paywall -->
    <div v-else-if="!isPremium" class="flex items-center justify-center min-h-[calc(100vh-41px)]">
      <div class="text-center">
        <h2 class="text-lg font-medium text-gray-200 mb-2">Premium Feature</h2>
        <p class="text-gray-400 text-sm mb-4">Norwood Certification requires a premium subscription.</p>
        <router-link to="/settings" class="text-purple-400 text-sm hover:underline">
          Upgrade to Premium
        </router-link>
      </div>
    </div>

    <!-- Cooldown -->
    <div v-else-if="cooldownDays > 0" class="flex items-center justify-center min-h-[calc(100vh-41px)]">
      <div class="text-center">
        <h2 class="text-lg font-medium text-gray-200 mb-2">Certification Cooldown</h2>
        <p class="text-gray-400 text-sm mb-2">You can only get certified once per month.</p>
        <p class="text-purple-400 text-lg font-medium">{{ cooldownDays }} days remaining</p>
      </div>
    </div>

    <!-- Main Content with Sidebar -->
    <div v-else class="flex">
      <!-- Sidebar: Certification History -->
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
          <span v-if="item.norwood_stage" class="text-[11px] font-bold text-purple-400 w-4">{{ item.norwood_stage }}{{ item.norwood_variant || '' }}</span>
        </template>
        <template #title="{ item }">{{ item.norwood_stage ? `Norwood ${item.norwood_stage}${item.norwood_variant || ''}` : 'In Progress' }}</template>
        <template #date="{ item }">{{ formatDateShort(item.certified_at) }}</template>
      </HistorySidebar>

      <!-- Main Content -->
      <main class="flex-1 p-6 h-[calc(100vh-41px)] overflow-y-auto">
        <div class="max-w-2xl mx-auto">
      <!-- Progress Steps -->
      <div class="flex items-center justify-center mb-8">
        <div v-for="(type, index) in [...photoTypes, 'result']" :key="type" class="flex items-center">
          <button
            @click="goToStep(index + 1)"
            class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors cursor-pointer hover:opacity-80"
            :class="{
              'bg-purple-600 text-white': step === index + 1,
              'bg-green-600 text-white': step > index + 1,
              'bg-gray-700 text-gray-400': step < index + 1
            }"
          >
            <span v-if="step > index + 1">✓</span>
            <span v-else>{{ index + 1 }}</span>
          </button>
          <div v-if="index < 3" class="w-8 h-0.5 bg-gray-700" :class="{ 'bg-green-600': step > index + 1 }"></div>
        </div>
      </div>

      <!-- Step Labels -->
      <div class="flex justify-between text-[10px] text-gray-500 mb-8 px-2">
        <span>Front</span>
        <span>Left</span>
        <span>Right</span>
        <span>Certificate</span>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="bg-red-900/30 border border-red-700 rounded px-4 py-2 mb-6 text-sm text-red-400">
        {{ error }}
      </div>

      <!-- Photo Upload Steps (1-3) -->
      <template v-if="step <= 3">
      <div :key="step" class="bg-gray-800 rounded-lg p-6">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-medium text-gray-200 capitalize">{{ currentPhotoType }} Photo</h3>
          <div class="flex items-center gap-3">
            <button
              v-if="step > 1"
              @click="prevStep"
              class="text-gray-400 hover:text-gray-200 text-xs"
            >
              ← Back
            </button>
            <button
              @click="restartCurrent"
              class="text-gray-500 hover:text-red-400 text-xs"
            >
              Start Over
            </button>
          </div>
        </div>
        <p class="text-gray-400 text-sm mb-6">{{ photoInstructions[currentPhotoType] }}</p>

        <!-- Already Approved State (not redoing) -->
        <div v-if="currentPhotoApproved && !isRedoing">
          <div class="bg-green-900/30 border border-green-700 rounded px-4 py-3 mb-4">
            <p class="text-green-400 text-sm font-medium mb-1">✓ Photo Already Approved</p>
            <p class="text-gray-400 text-xs">{{ currentPhoto.quality_notes }}</p>
          </div>

          <div class="flex gap-3">
            <button
              @click="startRedo"
              class="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition-colors"
            >
              Redo Photo
            </button>
            <button
              @click="nextStep"
              class="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded transition-colors"
            >
              Continue →
            </button>
          </div>
        </div>

        <!-- Upload New Photo State (not approved yet, or redoing) -->
        <div v-else>
          <!-- Cancel redo option -->
          <button
            v-if="isRedoing"
            @click="cancelRedo"
            class="text-gray-400 hover:text-gray-200 text-xs mb-4"
          >
            ← Cancel redo, keep existing photo
          </button>

          <!-- File Input -->
          <div class="mb-6">
            <input
              ref="fileInputRef"
              :key="`${step}-${isRedoing}`"
              type="file"
              accept="image/*"
              @change="handleFileSelect"
              :disabled="validating"
              class="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-purple-600 file:text-white hover:file:bg-purple-500 disabled:opacity-50"
            />
          </div>

          <!-- Preview -->
          <div v-if="preview" class="mb-6">
            <img :src="preview" class="max-h-64 rounded mx-auto" alt="Preview" />
          </div>

          <!-- Upload Button -->
          <button
            v-if="preview && !validating && !validationResult"
            @click="uploadPhoto"
            :disabled="uploading"
            class="w-full py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 text-white text-sm rounded transition-colors"
          >
            {{ uploading ? 'Uploading...' : 'Submit for Validation' }}
          </button>

          <!-- Validating -->
          <div v-if="validating" class="text-center py-4">
            <p class="text-gray-400 text-sm">Validating photo quality...</p>
            <div class="mt-2 w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
          </div>

          <!-- Validation Result -->
          <div v-if="validationResult" class="mt-6">
            <div
              v-if="validationResult.approved"
              class="bg-green-900/30 border border-green-700 rounded px-4 py-3"
            >
              <p class="text-green-400 text-sm font-medium">✓ Photo Approved</p>
            </div>

            <div
              v-else
              class="bg-red-900/30 border border-red-700 rounded px-4 py-3"
            >
              <p class="text-red-400 text-sm font-medium mb-1">✗ Photo Rejected</p>
              <p class="text-gray-400 text-xs mb-3">{{ validationResult.rejection_reason }}</p>
              <button
                @click="retake"
                class="text-purple-400 text-xs hover:underline"
              >
                Retake Photo
              </button>
            </div>
          </div>
        </div>
      </div>
      </template>

      <!-- Certificate Step (4) -->
      <div v-if="step === 4" class="bg-gray-800 rounded-lg p-6">
        <!-- Not yet generated -->
        <div v-if="certification?.status === 'photos_pending' && allPhotosApproved">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-lg font-medium text-gray-200">All Photos Approved!</h3>
            <button
              @click="prevStep"
              class="text-gray-400 hover:text-gray-200 text-xs"
            >
              ← Back
            </button>
          </div>
          <p class="text-gray-400 text-sm mb-6">Ready to generate your official Norwood certification.</p>

          <button
            @click="generateCertificate"
            :disabled="generating"
            class="w-full py-3 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 text-white font-medium rounded transition-colors"
          >
            {{ generating ? 'Generating Certificate...' : 'Generate Certificate' }}
          </button>
        </div>

        <!-- Generating -->
        <div v-else-if="certification?.status === 'analyzing' || generating" class="text-center py-8">
          <p class="text-gray-300 mb-4">Analyzing your photos and generating certificate...</p>
          <div class="w-12 h-12 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p class="text-gray-500 text-xs mt-4">This may take a minute</p>
        </div>

        <!-- Failed -->
        <div v-else-if="certification?.status === 'failed'" class="text-center py-8">
          <p class="text-red-400 mb-4">Certification failed. Please try again.</p>
          <button
            @click="startCertification"
            class="text-purple-400 text-sm hover:underline"
          >
            Start Over
          </button>
        </div>

        <!-- Completed -->
        <div v-else-if="certification?.status === 'completed'" class="text-center">
          <h2 class="text-2xl font-bold text-gray-100 mb-2">🎓 Certification Complete!</h2>

          <div class="my-8 p-6 bg-gray-900 rounded-lg border border-gray-700">
            <p class="text-gray-400 text-sm mb-2">You have been classified as</p>
            <p class="text-4xl font-bold text-purple-400 mb-2">
              Norwood {{ certification.norwood_stage }}{{ certification.norwood_variant || '' }}
            </p>
            <p class="text-gray-500 text-sm">
              Confidence: {{ Math.round(certification.confidence * 100) }}%
            </p>
          </div>

          <div class="text-left bg-gray-900 rounded-lg p-4 mb-6">
            <h4 class="text-sm font-medium text-gray-300 mb-2">Clinical Assessment</h4>
            <p class="text-gray-400 text-xs leading-relaxed">{{ certification.clinical_assessment }}</p>
          </div>

          <p class="text-gray-500 text-xs mb-4">Certified on {{ formatDate(certification.certified_at) }}</p>

          <a
            :href="certification.pdf_url"
            target="_blank"
            class="inline-block px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded transition-colors"
          >
            Download PDF Certificate
          </a>
        </div>
      </div>
      </div>
      </main>
    </div>
  </div>
</template>
