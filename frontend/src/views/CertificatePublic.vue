<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const certification = ref(null)
const loading = ref(true)
const error = ref(null)

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

onMounted(async () => {
  try {
    const res = await fetch(`${API_URL}/api/certification/public/${route.params.id}`)
    if (res.ok) {
      certification.value = await res.json()
    } else {
      error.value = 'Certification not found'
    }
  } catch (err) {
    error.value = 'Failed to load certification'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white flex items-center justify-center p-4">
    <div class="max-w-md w-full">
      <!-- Loading -->
      <div v-if="loading" class="text-center">
        <p class="text-gray-500 text-sm">Loading...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center">
        <p class="text-gray-400 text-sm">{{ error }}</p>
        <router-link to="/" class="text-purple-400 text-sm hover:underline mt-4 inline-block">
          Go to Norwood AI
        </router-link>
      </div>

      <!-- Certificate -->
      <div v-else class="bg-gray-800 rounded-lg p-8 text-center border border-gray-700">
        <h1 class="text-sm text-gray-500 uppercase tracking-wide mb-6">Norwood AI Certification</h1>

        <div class="my-8">
          <p class="text-gray-400 text-sm mb-2">Officially classified as</p>
          <p class="text-5xl font-bold text-purple-400 mb-2">
            Norwood {{ certification.norwood_stage }}{{ certification.norwood_variant || '' }}
          </p>
        </div>

        <p class="text-gray-500 text-xs">
          Certified on {{ formatDate(certification.certified_at) }}
        </p>

        <div class="mt-8 pt-6 border-t border-gray-700">
          <router-link to="/" class="text-purple-400 text-sm hover:underline">
            Get your own certification
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
