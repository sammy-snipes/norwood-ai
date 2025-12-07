<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const activeTab = ref('home')

const daysSinceLaunch = computed(() => {
  const launchDate = new Date('2025-12-05')
  const today = new Date()
  const diffTime = Math.abs(today - launchDate)
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white flex flex-col">
    <!-- Top Bar -->
    <header class="border-b border-gray-800 px-4 py-2">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-6">
          <span class="font-medium text-sm">Norwood AI</span>
          <nav class="flex gap-4">
            <button
              @click="activeTab = 'home'"
              :class="['text-xs transition-colors', activeTab === 'home' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300']"
            >
              Home
            </button>
            <button
              @click="activeTab = 'about'"
              :class="['text-xs transition-colors', activeTab === 'about' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300']"
            >
              About
            </button>
            <button
              @click="activeTab = 'testimonials'"
              :class="['text-xs transition-colors', activeTab === 'testimonials' ? 'text-gray-400' : 'text-gray-500 hover:text-gray-300']"
            >
              Testimonials
            </button>
          </nav>
        </div>
        <button
          @click="authStore.loginWithGoogle"
          class="flex items-center gap-2 px-3 py-1.5 bg-white text-gray-900 rounded text-xs font-medium hover:bg-gray-100 transition-all"
        >
          <svg class="w-3 h-3" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Sign in
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1">
      <!-- HOME TAB -->
      <div v-if="activeTab === 'home'" class="flex flex-col items-center justify-center px-4 py-12 text-center">
        <p class="text-base text-gray-400 mb-3 max-w-lg leading-relaxed italic">
          "A hairline unexamined is not worth having."
        </p>
        <p class="text-gray-500 text-sm mb-6 max-w-md leading-relaxed">
          We expose the fundamental entropy of your follicular existence.
        </p>

        <button
          @click="authStore.loginWithGoogle"
          class="px-5 py-2 bg-white text-gray-900 rounded text-sm font-medium hover:bg-gray-100 transition-all"
        >
          Confront Your Truth
        </button>

        <p class="mt-4 text-gray-600 text-xs italic">
          One free analysis. $5 for unlimited.
        </p>

        <!-- Philosophical excerpt -->
        <div class="mt-12 max-w-md p-6 border border-gray-800 rounded-lg">
          <p class="text-gray-400 text-sm leading-relaxed mb-4">
            The scalp remembers what the mirror refuses to show. We do not heal wounds here—we
            illuminate them. In naming the recession, we begin the quiet work of reconciliation.
          </p>
          <p class="text-gray-500 text-xs leading-relaxed">
            Some seek treatment. Others seek understanding. We offer neither salvation nor cure,
            only the peculiar comfort of precise measurement. To know the stage is to hold
            impermanence in one's hands, briefly, before it too recedes.
          </p>
        </div>

        <!-- Diagram -->
        <div class="mt-10 p-4 border border-gray-800 rounded-lg max-w-md w-full">
          <p class="text-gray-600 font-mono text-xs mb-3">THE NORWOOD-HEGELIAN DIALECTIC</p>
          <div class="flex items-center justify-between text-xs">
            <div class="text-center">
              <div class="text-gray-500">Thesis</div>
              <div class="text-gray-300 font-medium mt-0.5">"I'm not balding"</div>
            </div>
            <div class="text-gray-700">→</div>
            <div class="text-center">
              <div class="text-gray-500">Antithesis</div>
              <div class="text-gray-300 font-medium mt-0.5">"The photos"</div>
            </div>
            <div class="text-gray-700">→</div>
            <div class="text-center">
              <div class="text-gray-500">Synthesis</div>
              <div class="text-gray-300 font-medium mt-0.5">"Acceptance"</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ABOUT TAB -->
      <div v-if="activeTab === 'about'" class="max-w-xl mx-auto px-4 py-12">
        <h2 class="text-xl font-bold mb-6 text-center">About</h2>

        <div class="space-y-4 text-gray-400 text-sm leading-relaxed">
          <p>
            Norwood AI emerged from the void <span class="font-bold text-gray-300">{{ daysSinceLaunch }}</span> days ago. The Norwood scale is not merely a classification system,
            but a <em>phenomenological framework</em> for understanding human impermanence.
          </p>

          <p>
            Our AI has been trained on millions of hairlines and the complete works of Emil Cioran.
            It does not merely <em>see</em> your baldness—it <em>grasps</em> it in its totality.
          </p>

          <p class="text-gray-500 italic text-xs">
            Hell is the bathroom mirror at 7 AM under fluorescent lighting.
          </p>

          <div class="mt-8 p-4 bg-gray-800/50 rounded-lg">
            <h3 class="font-medium text-sm mb-2 text-gray-300">Our Mission</h3>
            <p class="text-gray-500 text-xs">
              To democratize follicular truth.
            </p>
          </div>
        </div>
      </div>

      <!-- TESTIMONIALS TAB -->
      <div v-if="activeTab === 'testimonials'" class="max-w-2xl mx-auto px-4 py-12">
        <h2 class="text-xl font-bold mb-6 text-center">Testimonials</h2>

        <div class="grid md:grid-cols-2 gap-3">
          <div class="p-3 bg-gray-800/50 rounded-lg">
            <p class="text-gray-400 text-xs mb-2">
              "I came for a hairline analysis. I left questioning the nature of identity itself."
            </p>
            <p class="text-gray-600 text-xs">— Marcus T., Stage 4</p>
          </div>

          <div class="p-3 bg-gray-800/50 rounded-lg">
            <p class="text-gray-400 text-xs mb-2">
              "It said my head looked like 'a knee with anxiety.' Worth every penny."
            </p>
            <p class="text-gray-600 text-xs">— David R., Stage 5</p>
          </div>

          <div class="p-3 bg-gray-800/50 rounded-lg">
            <p class="text-gray-400 text-xs mb-2">
              "I have stared into the chrome abyss and the chrome abyss has stared back."
            </p>
            <p class="text-gray-600 text-xs">— Jason K., Stage 3V</p>
          </div>

          <div class="p-3 bg-gray-800/50 rounded-lg">
            <p class="text-gray-400 text-xs mb-2">
              "My wife saw the analysis and agreed with it. She hasn't spoken to me in days."
            </p>
            <p class="text-gray-600 text-xs">— Anthony M., Stage 6</p>
          </div>

          <div class="p-3 bg-gray-800/50 rounded-lg">
            <p class="text-gray-400 text-xs mb-2">
              "I shared my cock certification on LinkedIn. HR called me within the hour. Worth it."
            </p>
            <p class="text-gray-600 text-xs">— Kevin L., Zone B</p>
          </div>
        </div>

        <p class="mt-6 text-center text-gray-600 text-xs italic">
          * All testimonials are real.
        </p>
      </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-gray-800 py-3 px-4 text-center text-gray-600 text-xs">
      <p>A hairline unexamined is not worth having.</p>
    </footer>
  </div>
</template>
