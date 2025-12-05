<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const error = ref(null)

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const hasUnlimited = computed(() => {
  return authStore.user?.is_admin || authStore.user?.is_premium
})

const handleLogout = () => {
  authStore.logout()
  router.push('/')
}

const upgradeToPremium = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await fetch(`${API_URL}/api/payments/create-checkout-session`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to create checkout session')
    }

    const data = await response.json()
    // Open Stripe Checkout in new tab
    window.open(data.checkout_url, '_blank')
    loading.value = false
  } catch (err) {
    error.value = err.message
    loading.value = false
  }
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
            <router-link to="/analyze" class="text-xs text-gray-500 hover:text-gray-300 transition-colors">
              Analyze
            </router-link>
            <router-link to="/settings" class="text-xs text-gray-400 hover:text-white transition-colors">
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

    <!-- Main Content -->
    <main class="max-w-xl mx-auto px-4 py-8">
      <h1 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Settings</h1>

      <div class="space-y-8">
        <!-- Premium Status -->
        <div class="p-8 bg-gray-800/50 rounded-lg border border-gray-700">
          <div class="flex items-start justify-between">
            <div>
              <h2 class="text-xl font-bold mb-2">
                <span v-if="authStore.user?.is_premium" class="text-yellow-400">✨ Premium Member</span>
                <span v-else class="text-gray-400">Free Account</span>
              </h2>

              <p v-if="authStore.user?.is_premium" class="text-gray-400">
                Unlimited analyses. You're living the dream.
              </p>
              <p v-else class="text-gray-400">
                Free analyses remaining: <span class="font-bold text-white">{{ authStore.user?.free_analyses_remaining || 0 }}</span>
              </p>
            </div>

            <button
              v-if="!authStore.user?.is_premium"
              @click="upgradeToPremium"
              :disabled="loading"
              class="px-6 py-3 bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 rounded-lg font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="loading">Processing...</span>
              <span v-else>Upgrade to Premium - $5</span>
            </button>
          </div>

          <div v-if="error" class="mt-4 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
            {{ error }}
          </div>

          <div v-if="!authStore.user?.is_premium" class="mt-6 pt-6 border-t border-gray-700">
            <h3 class="font-bold mb-3 text-gray-300">Premium Features:</h3>
            <ul class="space-y-2 text-gray-400">
              <li>✓ Unlimited hair loss analyses</li>
              <li>✓ Unlimited existential crises</li>
              <li>✓ Unlimited savage roasts</li>
              <li>✓ One-time payment, no subscription</li>
            </ul>
          </div>
        </div>


        <!-- The Criticism -->
        <div class="p-4 bg-gray-800/50 rounded-lg">
          <h2 class="text-sm font-medium mb-3 text-red-400">A Note on Your Presence Here</h2>

          <div class="space-y-3 text-sm text-gray-400 leading-relaxed">
            <p>You clicked on "Settings."</p>

            <p>
              Let that sink in. Of all the things you could be doing with your finite existence on this
              spinning rock—reading Kierkegaard, calling your mother, confronting the encroaching void
              of your hairline—you chose to visit a <em>settings page</em>.
            </p>

            <p>
              What did you expect to find here? A toggle to make your hair grow back?
              A slider labeled "Denial Intensity"? Perhaps a dropdown menu for "Preferred Coping Mechanisms"?
            </p>

            <p>
              There is nothing here. There was never going to be anything here.
              The settings page is, much like your hairline, an elaborate illusion of control
              over forces beyond your comprehension.
            </p>

            <p class="text-gray-500 italic text-xs">
              Hegel wrote that "the owl of Minerva spreads its wings only with the falling of the dusk."
              You, however, have spread your wings to visit a settings page at what I can only assume
              is some ungodly hour, seeking customization options for a baldness classifier.
            </p>

            <p>The only setting you need to adjust is your expectations for life.</p>
          </div>
        </div>

        <!-- Fake Settings That Do Nothing -->
        <div class="p-4 bg-gray-800/30 rounded-lg opacity-50">
          <h3 class="text-xs font-medium mb-3 text-gray-500">Notification Preferences</h3>
          <div class="space-y-2">
            <label class="flex items-center gap-2 cursor-not-allowed">
              <input type="checkbox" disabled class="cursor-not-allowed w-3 h-3" />
              <span class="text-xs text-gray-600">Email me when my hairline recedes further</span>
            </label>
            <label class="flex items-center gap-2 cursor-not-allowed">
              <input type="checkbox" disabled class="cursor-not-allowed w-3 h-3" />
              <span class="text-xs text-gray-600">Daily existential crisis reminders</span>
            </label>
            <label class="flex items-center gap-2 cursor-not-allowed">
              <input type="checkbox" disabled class="cursor-not-allowed w-3 h-3" />
              <span class="text-xs text-gray-600">Notify me when hope is objectively lost</span>
            </label>
          </div>
          <p class="mt-3 text-xs text-gray-600 italic">
            (These don't do anything. Why would they?)
          </p>
        </div>

        <!-- Back Button -->
        <div class="text-center pt-4">
          <router-link
            to="/analyze"
            class="inline-block px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors"
          >
            Return to What Matters
          </router-link>
        </div>
      </div>
    </main>
  </div>
</template>
