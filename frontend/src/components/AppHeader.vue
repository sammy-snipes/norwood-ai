<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['donate'])

const router = useRouter()
const authStore = useAuthStore()

const menuOpen = ref(false)
const menuRef = ref(null)

const hasUnlimited = computed(() => {
  return authStore.user?.is_admin || authStore.user?.is_premium
})

const handleLogout = () => {
  menuOpen.value = false
  authStore.logout()
  router.push('/')
}

const goToSettings = () => {
  menuOpen.value = false
  router.push('/settings')
}

const handleDonate = () => {
  menuOpen.value = false
  emit('donate')
}

const handleClickOutside = (e) => {
  if (menuRef.value && !menuRef.value.contains(e.target)) {
    menuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
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
            class="text-xs transition-colors flex items-center gap-1"
            :class="$route.path === '/counseling' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300'"
          >
            Counseling
            <span v-if="!hasUnlimited" class="text-[8px] text-purple-400 bg-purple-900/50 px-0.5 rounded leading-tight">sage</span>
          </router-link>
          <router-link
            to="/certification"
            class="text-xs transition-colors flex items-center gap-1"
            :class="$route.path === '/certification' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300'"
          >
            Certification
            <span v-if="!hasUnlimited" class="text-[8px] text-purple-400 bg-purple-900/50 px-0.5 rounded leading-tight">sage</span>
          </router-link>
          <router-link
            to="/leaderboard"
            class="text-xs transition-colors flex items-center gap-1"
            :class="$route.path === '/leaderboard' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300'"
          >
            Leaderboard
            <span v-if="!hasUnlimited" class="text-[8px] text-purple-400 bg-purple-900/50 px-0.5 rounded leading-tight">sage</span>
          </router-link>
        </nav>
      </div>

      <!-- Donate + Gear Menu -->
      <div class="flex items-center gap-2">
        <button
          @click="emit('donate')"
          class="px-2 py-1 text-xs text-purple-300 bg-purple-900/50 hover:bg-purple-800/50 rounded transition-colors"
        >
          donate
        </button>

        <div ref="menuRef" class="relative">
        <button
          @click="menuOpen = !menuOpen"
          class="p-1.5 text-gray-500 hover:text-gray-300 transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>

        <!-- Dropdown -->
        <div
          v-if="menuOpen"
          class="absolute right-0 top-full mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg py-1 z-50"
        >
          <!-- User Info -->
          <div class="px-3 py-2 border-b border-gray-700">
            <div class="flex items-center gap-2">
              <img
                v-if="authStore.user?.avatar_url"
                :src="authStore.user.avatar_url"
                class="w-6 h-6 rounded-full"
              />
              <div v-else class="w-6 h-6 rounded-full bg-gray-600"></div>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-gray-200 truncate">{{ authStore.user?.name }}</p>
                <p v-if="hasUnlimited" class="text-[10px] text-purple-400">
                  {{ authStore.user?.is_admin ? 'Admin' : 'Sage Mode' }}
                </p>
                <p v-else class="text-[10px] text-gray-500">
                  {{ authStore.user?.free_analyses_remaining }} free remaining
                </p>
              </div>
            </div>
          </div>

          <!-- Menu Items -->
          <button
            @click="goToSettings"
            class="w-full px-3 py-2 text-left text-xs text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors"
          >
            Settings
          </button>

          <button
            v-if="!hasUnlimited"
            @click="goToSettings"
            class="w-full px-3 py-2 text-left text-xs text-purple-400 hover:bg-gray-700 transition-colors"
          >
            Enter Sage Mode
          </button>

          <button
            @click="handleDonate"
            class="w-full px-3 py-2 text-left text-xs text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors"
          >
            Donate
          </button>

          <div class="border-t border-gray-700 mt-1 pt-1">
            <button
              @click="handleLogout"
              class="w-full px-3 py-2 text-left text-xs text-gray-500 hover:bg-gray-700 hover:text-gray-300 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
      </div>
    </div>
  </header>
</template>
