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
    <main class="max-w-2xl mx-auto px-4 py-20">
      <h1 class="text-4xl font-black mb-8 text-center">Settings</h1>

      <div class="space-y-8">
        <!-- The Criticism -->
        <div class="p-8 bg-gray-800/50 rounded-lg border border-gray-700">
          <h2 class="text-xl font-bold mb-4 text-red-400">A Note on Your Presence Here</h2>

          <div class="space-y-4 text-gray-300 leading-relaxed">
            <p>
              You clicked on "Settings."
            </p>

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

            <p class="text-gray-500 italic">
              Hegel wrote that "the owl of Minerva spreads its wings only with the falling of the dusk."
              You, however, have spread your wings to visit a settings page at what I can only assume
              is some ungodly hour, seeking customization options for a baldness classifier.
            </p>

            <p>
              The only setting you need to adjust is your expectations for life.
            </p>
          </div>
        </div>

        <!-- Fake Settings That Do Nothing -->
        <div class="p-6 bg-gray-800/30 rounded-lg opacity-50">
          <h3 class="font-bold mb-4 text-gray-500">Notification Preferences</h3>
          <div class="space-y-3">
            <label class="flex items-center gap-3 cursor-not-allowed">
              <input type="checkbox" disabled class="cursor-not-allowed" />
              <span class="text-gray-600">Email me when my hairline recedes further</span>
            </label>
            <label class="flex items-center gap-3 cursor-not-allowed">
              <input type="checkbox" disabled class="cursor-not-allowed" />
              <span class="text-gray-600">Daily existential crisis reminders</span>
            </label>
            <label class="flex items-center gap-3 cursor-not-allowed">
              <input type="checkbox" disabled class="cursor-not-allowed" />
              <span class="text-gray-600">Notify me when hope is objectively lost</span>
            </label>
          </div>
          <p class="mt-4 text-xs text-gray-600 italic">
            (These don't do anything. Why would they?)
          </p>
        </div>

        <!-- Back Button -->
        <div class="text-center pt-8">
          <router-link
            to="/analyze"
            class="inline-block px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition-colors"
          >
            Return to What Matters (Your Hairline)
          </router-link>
        </div>
      </div>
    </main>
  </div>
</template>
