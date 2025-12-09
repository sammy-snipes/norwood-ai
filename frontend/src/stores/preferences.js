import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useAuthStore } from './auth'

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

export const usePreferencesStore = defineStore('preferences', () => {
  const adultContentEnabled = ref(false)

  const authStore = useAuthStore()

  // Sync from user data when it changes
  watch(() => authStore.user, (user) => {
    if (user) {
      adultContentEnabled.value = user.adult_content_enabled || false
    } else {
      adultContentEnabled.value = false
    }
  }, { immediate: true })

  async function setAdultContentEnabled(value) {
    adultContentEnabled.value = value

    // Persist to backend if authenticated
    if (authStore.token) {
      try {
        await fetch(`${API_URL}/api/auth/adult-content`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authStore.token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ enabled: value })
        })
      } catch (err) {
        console.error('Failed to save adult content preference:', err)
      }
    }
  }

  return {
    adultContentEnabled,
    setAdultContentEnabled
  }
})
