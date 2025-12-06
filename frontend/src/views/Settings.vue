<script setup>
import { useAuthStore } from '../stores/auth'
import AppHeader from '../components/AppHeader.vue'

const authStore = useAuthStore()
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <AppHeader />

    <!-- Main Content -->
    <main class="h-[calc(100vh-41px)] overflow-y-auto">
      <div class="max-w-xl mx-auto px-4 py-8">
      <h1 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Settings</h1>

      <div class="space-y-4">
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
      </div>
    </main>
  </div>
</template>
