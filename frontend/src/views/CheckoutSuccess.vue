<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  // Refresh user data to get updated premium status
  await authStore.fetchUser()

  // Redirect to settings after 3 seconds
  setTimeout(() => {
    router.push('/settings')
  }, 3000)
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white flex items-center justify-center px-4">
    <div class="max-w-md w-full text-center space-y-6">
      <div class="text-6xl mb-4">✨</div>

      <h1 class="text-4xl font-black mb-4">Welcome to Premium!</h1>

      <div class="p-6 bg-gray-800/50 rounded-lg border border-gray-700 space-y-4">
        <p class="text-gray-300 leading-relaxed">
          Congratulations. You've just paid $5 to unlock unlimited analyses of your receding hairline.
        </p>

        <p class="text-gray-400 text-sm">
          Some might question this decision. We won't. Your money is in our account now.
        </p>

        <div class="pt-4 border-t border-gray-700">
          <p class="text-yellow-400 font-bold mb-2">Premium Benefits Unlocked:</p>
          <ul class="text-gray-400 text-sm space-y-1">
            <li>✓ Unlimited analyses</li>
            <li>✓ Unlimited roasts</li>
            <li>✓ Unlimited existential dread</li>
          </ul>
        </div>
      </div>

      <p class="text-gray-500 text-sm">
        Redirecting to settings in 3 seconds...
      </p>

      <router-link
        to="/settings"
        class="inline-block px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition-colors"
      >
        Go to Settings Now
      </router-link>
    </div>
  </div>
</template>
