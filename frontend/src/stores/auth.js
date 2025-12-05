import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token'))
  const loading = ref(true) // Start true until we check auth
  const initialized = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  async function fetchUser() {
    if (!token.value) {
      loading.value = false
      return null
    }

    loading.value = true
    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      })

      if (response.ok) {
        user.value = await response.json()
        return user.value
      } else {
        // Token invalid, clear it
        logout()
        return null
      }
    } catch (err) {
      console.error('Failed to fetch user:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  function loginWithGoogle() {
    window.location.href = `${API_URL}/api/auth/google`
  }

  // Initialize - check for token in URL (OAuth callback)
  async function init() {
    if (initialized.value) return

    const urlParams = new URLSearchParams(window.location.search)
    const urlToken = urlParams.get('token')

    if (urlToken) {
      setToken(urlToken)
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname)
    }

    if (token.value) {
      await fetchUser()
    } else {
      loading.value = false
    }

    initialized.value = true
  }

  return {
    user,
    token,
    loading,
    initialized,
    isAuthenticated,
    fetchUser,
    setToken,
    logout,
    loginWithGoogle,
    init
  }
})
