<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import AppHeader from '../components/AppHeader.vue'
import DonateToast from '../components/DonateToast.vue'

const authStore = useAuthStore()
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

const loading = ref(true)
const leaderboard = ref(null)
const showDonateToast = ref(false)

const isPremium = computed(() => authStore.user?.is_premium || authStore.user?.is_admin)

const maxInsecurityScore = computed(() => {
  if (!leaderboard.value?.insecurity_index?.length) return 1
  return leaderboard.value.insecurity_index[0]?.score || 1
})

const fetchLeaderboard = async () => {
  try {
    const res = await fetch(`${API_URL}/api/leaderboard`, {
      headers: { 'Authorization': `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      leaderboard.value = await res.json()
    }
  } catch (err) {
    console.error('Failed to fetch leaderboard:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (isPremium.value) {
    fetchLeaderboard()
  } else {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <AppHeader @donate="showDonateToast = true" />

    <main class="p-6 h-[calc(100vh-41px)] overflow-y-auto">
      <!-- Paywall -->
      <div v-if="!isPremium" class="flex items-center justify-center h-full">
        <div class="text-center">
          <h2 class="text-lg font-medium text-gray-200 mb-2">Sage Mode Feature</h2>
          <p class="text-gray-400 text-sm mb-4">Leaderboard requires Sage Mode.</p>
          <router-link to="/settings" class="text-purple-400 text-xs hover:underline">
            Enter Sage Mode
          </router-link>
        </div>
      </div>

      <div v-else class="max-w-4xl mx-auto">
        <h1 class="text-xl font-semibold text-gray-300 mb-8">Leaderboard</h1>

        <!-- Loading -->
        <div v-if="loading" class="text-center py-12">
          <p class="text-gray-500 text-sm">Loading...</p>
        </div>

        <div v-else-if="leaderboard" class="space-y-10">
          <!-- Norwood Rankings: Two Columns -->
          <div class="grid grid-cols-2 gap-8">
            <!-- Best Norwood -->
            <div class="bg-gray-800/50 rounded-lg p-5">
              <h2 class="text-sm font-medium text-green-400 mb-4">Best Norwood</h2>
              <p class="text-gray-500 text-xs mb-4">Users with the most hair (lowest stage)</p>

              <div v-if="leaderboard.best_norwood.length" class="space-y-3">
                <div
                  v-for="(entry, index) in leaderboard.best_norwood"
                  :key="index"
                  class="flex items-center gap-3"
                >
                  <span class="text-gray-500 text-xs w-4">{{ index + 1 }}</span>
                  <img
                    v-if="entry.avatar_url"
                    :src="entry.avatar_url"
                    class="w-6 h-6 rounded-full"
                  />
                  <div v-else class="w-6 h-6 rounded-full bg-gray-700"></div>
                  <span class="text-gray-300 text-sm flex-1 truncate">{{ entry.username }}</span>
                  <span class="text-green-400 font-bold">{{ entry.norwood_stage }}</span>
                </div>
              </div>
              <p v-else class="text-gray-600 text-xs">No data yet</p>
            </div>

            <!-- Worst Norwood -->
            <div class="bg-gray-800/50 rounded-lg p-5">
              <h2 class="text-sm font-medium text-red-400 mb-4">Worst Norwood</h2>
              <p class="text-gray-500 text-xs mb-4">Users embracing the void (highest stage)</p>

              <div v-if="leaderboard.worst_norwood.length" class="space-y-3">
                <div
                  v-for="(entry, index) in leaderboard.worst_norwood"
                  :key="index"
                  class="flex items-center gap-3"
                >
                  <span class="text-gray-500 text-xs w-4">{{ index + 1 }}</span>
                  <img
                    v-if="entry.avatar_url"
                    :src="entry.avatar_url"
                    class="w-6 h-6 rounded-full"
                  />
                  <div v-else class="w-6 h-6 rounded-full bg-gray-700"></div>
                  <span class="text-gray-300 text-sm flex-1 truncate">{{ entry.username }}</span>
                  <span class="text-red-400 font-bold">{{ entry.norwood_stage }}</span>
                </div>
              </div>
              <p v-else class="text-gray-600 text-xs">No data yet</p>
            </div>
          </div>

          <!-- Insecurity Index -->
          <div class="bg-gray-800/50 rounded-lg p-5">
            <h2 class="text-sm font-medium text-purple-400 mb-4">Insecurity Index</h2>
            <p class="text-gray-500 text-xs mb-6">
              Ranked by a proprietary algorithm developed by our intern's stepdad's dog (RIP)
            </p>

            <div v-if="leaderboard.insecurity_index.length" class="space-y-3">
              <div
                v-for="(entry, index) in leaderboard.insecurity_index"
                :key="index"
                class="flex items-center gap-3"
              >
                <span class="text-gray-500 text-xs w-4">{{ index + 1 }}</span>
                <img
                  v-if="entry.avatar_url"
                  :src="entry.avatar_url"
                  class="w-6 h-6 rounded-full flex-shrink-0"
                />
                <div v-else class="w-6 h-6 rounded-full bg-gray-700 flex-shrink-0"></div>
                <span class="text-gray-300 text-sm w-32 truncate">{{ entry.username }}</span>
                <div class="flex-1 h-5 bg-gray-700 rounded overflow-hidden">
                  <div
                    class="h-full bg-purple-600 transition-all"
                    :style="{ width: `${(entry.score / maxInsecurityScore) * 100}%` }"
                  ></div>
                </div>
                <span class="text-gray-400 text-xs w-12 text-right">{{ entry.score }}</span>
              </div>
            </div>
            <p v-else class="text-gray-600 text-xs">No data yet</p>
          </div>

          <!-- Cock Power Rankings -->
          <div class="grid grid-cols-2 gap-8">
            <!-- Pleasure Zone Rankings -->
            <div class="bg-gray-800/50 rounded-lg p-5">
              <h2 class="text-sm font-medium text-pink-400 mb-4">Cock Power: Pleasure</h2>
              <p class="text-gray-500 text-xs mb-4">Ranked by female pleasure zone (A is best)</p>

              <div v-if="leaderboard.cock_pleasure?.length" class="space-y-3">
                <div
                  v-for="(entry, index) in leaderboard.cock_pleasure"
                  :key="index"
                  class="flex items-center gap-3"
                >
                  <span class="text-gray-500 text-xs w-4">{{ index + 1 }}</span>
                  <img
                    v-if="entry.avatar_url"
                    :src="entry.avatar_url"
                    class="w-6 h-6 rounded-full"
                  />
                  <div v-else class="w-6 h-6 rounded-full bg-gray-700"></div>
                  <span class="text-gray-300 text-sm flex-1 truncate">{{ entry.username }}</span>
                  <span class="text-pink-400 font-bold text-xs">{{ entry.pleasure_zone_label }}</span>
                </div>
              </div>
              <p v-else class="text-gray-600 text-xs">No data yet</p>
            </div>

            <!-- Size Rankings -->
            <div class="bg-gray-800/50 rounded-lg p-5">
              <h2 class="text-sm font-medium text-orange-400 mb-4">Cock Power: Size</h2>
              <p class="text-gray-500 text-xs mb-4">Ranked by volumetric displacement</p>

              <div v-if="leaderboard.cock_size?.length" class="space-y-3">
                <div
                  v-for="(entry, index) in leaderboard.cock_size"
                  :key="index"
                  class="flex items-center gap-3"
                >
                  <span class="text-gray-500 text-xs w-4">{{ index + 1 }}</span>
                  <img
                    v-if="entry.avatar_url"
                    :src="entry.avatar_url"
                    class="w-6 h-6 rounded-full"
                  />
                  <div v-else class="w-6 h-6 rounded-full bg-gray-700"></div>
                  <span class="text-gray-300 text-sm flex-1 truncate">{{ entry.username }}</span>
                  <span class="text-orange-400 font-bold text-xs">{{ entry.length_inches.toFixed(1) }}" x {{ entry.girth_inches.toFixed(1) }}"</span>
                </div>
              </div>
              <p v-else class="text-gray-600 text-xs">No data yet</p>
            </div>
          </div>
        </div>
      </div>
    </main>

    <DonateToast
      v-if="showDonateToast"
      @close="showDonateToast = false"
      @donate="showDonateToast = false"
    />
  </div>
</template>
