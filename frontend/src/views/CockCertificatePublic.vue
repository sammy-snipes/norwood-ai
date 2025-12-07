<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const certification = ref(null)
const loading = ref(true)
const error = ref(null)

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

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

onMounted(async () => {
  const certId = route.params.id
  try {
    const res = await fetch(`${API_URL}/api/cock/public/${certId}`)
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
    <!-- Loading -->
    <div v-if="loading" class="text-center">
      <p class="text-gray-500 text-sm">Loading...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center">
      <p class="text-red-400 mb-4">{{ error }}</p>
      <router-link to="/" class="text-purple-400 text-sm hover:underline">
        Go Home
      </router-link>
    </div>

    <!-- Certificate -->
    <div v-else class="max-w-md w-full bg-gray-800 rounded-lg p-8 text-center">
      <h1 class="text-2xl font-bold text-gray-100 mb-6">🍆 Cock Certification</h1>

      <div class="my-8 p-6 bg-gray-900 rounded-lg border border-gray-700">
        <p class="text-gray-400 text-sm mb-2">Classified in</p>
        <p class="text-5xl font-bold mb-2" :class="getZoneColor(certification.pleasure_zone)">
          Zone {{ certification.pleasure_zone?.charAt(0).toUpperCase() || '?' }}
        </p>
        <p class="text-xl text-gray-300">"{{ certification.pleasure_zone_label }}"</p>

        <div class="grid grid-cols-2 gap-4 text-center mt-6 pt-4 border-t border-gray-700">
          <div>
            <p class="text-2xl font-bold text-purple-400">{{ certification.length_inches?.toFixed(1) }}"</p>
            <p class="text-gray-500 text-xs">Length</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-purple-400">{{ certification.girth_inches?.toFixed(1) }}"</p>
            <p class="text-gray-500 text-xs">Girth</p>
          </div>
        </div>

        <div class="mt-4 pt-4 border-t border-gray-700">
          <p class="text-lg text-purple-400">{{ certification.size_category?.replace('_', ' ') }}</p>
          <p class="text-gray-500 text-xs">Size Category</p>
        </div>
      </div>

      <p class="text-gray-500 text-xs mb-6">
        Certified on {{ formatDate(certification.certified_at) }}
      </p>

      <div class="border-t border-gray-700 pt-6">
        <p class="text-gray-400 text-sm mb-2">Get your own certification at</p>
        <router-link to="/" class="text-purple-400 font-medium hover:underline">
          NorwoodAI.com
        </router-link>
      </div>
    </div>
  </div>
</template>
