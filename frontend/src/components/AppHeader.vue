<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const hasUnlimited = computed(() => {
  return authStore.user?.is_admin || authStore.user?.is_premium
})

const handleLogout = () => {
  authStore.logout()
  router.push('/')
}
</script>

<template>
  <header class="border-b border-gray-800 px-4 py-2">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-6">
        <router-link to="/analyze" class="font-medium text-sm">
          Norwood AI
        </router-link>
        <nav class="flex gap-4">
          <router-link
            to="/analyze"
            class="text-xs transition-colors"
            :class="$route.path === '/analyze' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300'"
          >
            Analyze
          </router-link>
          <router-link
            to="/counseling"
            class="text-xs transition-colors"
            :class="$route.path === '/counseling' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300'"
          >
            Counseling
          </router-link>
          <router-link
            to="/settings"
            class="text-xs transition-colors"
            :class="$route.path === '/settings' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300'"
          >
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
</template>
