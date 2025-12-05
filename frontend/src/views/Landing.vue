<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const activeTab = ref('home')

const norwoodImages = [
  '/img/stage_1.png',
  '/img/stage_2.png',
  '/img/stage_3.png',
  '/img/stage_3v.png',
  '/img/stage_4.png',
  '/img/stage_5.png',
  '/img/stage_6.png',
  '/img/stage_7.png',
]

const currentFrame = ref(0)
let animationInterval = null

onMounted(() => {
  animationInterval = setInterval(() => {
    currentFrame.value = (currentFrame.value + 1) % norwoodImages.length
  }, 1200)
})

onUnmounted(() => {
  if (animationInterval) clearInterval(animationInterval)
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white flex flex-col">
    <!-- Top Bar -->
    <header class="border-b border-gray-800 px-6 py-4">
      <div class="max-w-6xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-8">
          <div class="flex items-center gap-2">
            <span class="font-bold text-xl">Norwood AI</span>
          </div>
          <nav class="flex gap-6">
            <button
              @click="activeTab = 'home'"
              :class="['text-sm transition-colors', activeTab === 'home' ? 'text-white' : 'text-gray-500 hover:text-gray-300']"
            >
              Home
            </button>
            <button
              @click="activeTab = 'about'"
              :class="['text-sm transition-colors', activeTab === 'about' ? 'text-white' : 'text-gray-500 hover:text-gray-300']"
            >
              About Us
            </button>
            <button
              @click="activeTab = 'testimonials'"
              :class="['text-sm transition-colors', activeTab === 'testimonials' ? 'text-white' : 'text-gray-500 hover:text-gray-300']"
            >
              Testimonials
            </button>
          </nav>
        </div>
        <button
          @click="authStore.loginWithGoogle"
          class="flex items-center gap-2 px-4 py-2 bg-white text-gray-900 rounded-lg font-medium text-sm hover:bg-gray-100 transition-all"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1">
      <!-- HOME TAB -->
      <div v-if="activeTab === 'home'" class="flex flex-col items-center justify-center px-4 py-20 text-center">
        <!-- Animated Norwood stages slideshow -->
        <div class="mb-8">
          <div class="w-32 h-32 relative">
            <img
              v-for="(img, i) in norwoodImages"
              :key="i"
              :src="img"
              :class="['absolute inset-0 w-full h-full object-contain transition-opacity duration-300 invert', currentFrame === i ? 'opacity-100' : 'opacity-0']"
              alt="Norwood scale"
            />
          </div>
          <p class="text-gray-600 font-mono text-xs mt-4">Stage {{ currentFrame + 1 }}/{{ norwoodImages.length }}</p>
        </div>

        <p class="text-xl md:text-2xl text-gray-300 mb-4 max-w-2xl leading-relaxed italic">
          "A hairline unexamined is not worth having."
        </p>
        <p class="text-gray-500 mb-8 max-w-xl leading-relaxed">
          We don't just classify baldness. We expose the fundamental entropy of your follicular existence.
          Heidegger wept. Your barber knew.
        </p>

        <button
          @click="authStore.loginWithGoogle"
          class="group px-8 py-4 bg-white text-gray-900 rounded-full font-bold text-lg hover:bg-gray-100 transition-all hover:scale-105 shadow-xl"
        >
          Confront Your Truth
        </button>

        <p class="mt-6 text-gray-600 text-sm italic">
          "One free glimpse into the abyss. $5 for unlimited existential dread."
        </p>

        <!-- Features as unhinged philosophical concepts -->
        <div class="mt-20 grid md:grid-cols-3 gap-8 text-center max-w-4xl">
          <div class="p-6 border border-gray-800 rounded-lg">
            <div class="text-gray-600 font-mono text-xs mb-3">fig. 1</div>
            <h3 class="font-bold text-lg mb-2">Brutal Precision</h3>
            <p class="text-gray-500 text-sm">Norwood stages 1-7, mapped to your psychological dissolution</p>
            <p class="text-gray-700 text-xs mt-3 italic">"That which does not kill your follicles makes you shinier"</p>
          </div>
          <div class="p-6 border border-gray-800 rounded-lg">
            <div class="text-gray-600 font-mono text-xs mb-3">fig. 2</div>
            <h3 class="font-bold text-lg mb-2">The Verdict</h3>
            <p class="text-gray-500 text-sm">AI-generated devastation that would make Nietzsche uncomfortable</p>
            <p class="text-gray-700 text-xs mt-3 italic">"God is dead and so is your hairline"</p>
          </div>
          <div class="p-6 border border-gray-800 rounded-lg">
            <div class="text-gray-600 font-mono text-xs mb-3">fig. 3</div>
            <h3 class="font-bold text-lg mb-2">Temporal Projections</h3>
            <p class="text-gray-500 text-sm">Witness your future. The chrome dome awaits. (Premium)</p>
            <p class="text-gray-700 text-xs mt-3 italic">"Time reveals all truths, especially cranial ones"</p>
          </div>
        </div>

        <!-- Unhinged diagram -->
        <div class="mt-16 p-8 border border-gray-800 rounded-lg max-w-2xl w-full">
          <p class="text-gray-600 font-mono text-xs mb-4">THE NORWOOD-HEGELIAN DIALECTIC</p>
          <div class="flex items-center justify-between text-sm">
            <div class="text-center">
              <div class="text-gray-400">Thesis</div>
              <div class="text-white font-bold mt-1">"I'm not balding"</div>
            </div>
            <div class="text-gray-700">→</div>
            <div class="text-center">
              <div class="text-gray-400">Antithesis</div>
              <div class="text-white font-bold mt-1">"The photos"</div>
            </div>
            <div class="text-gray-700">→</div>
            <div class="text-center">
              <div class="text-gray-400">Synthesis</div>
              <div class="text-white font-bold mt-1">"Acceptance"</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ABOUT TAB -->
      <div v-if="activeTab === 'about'" class="max-w-3xl mx-auto px-4 py-20">
        <h2 class="text-4xl font-black mb-8 text-center">About Us</h2>

        <div class="space-y-6 text-gray-300 leading-relaxed">
          <p>
            Norwood AI emerged from the void in 2024, founded by a collective of researchers who understood
            that the Norwood scale was not merely a classification system, but a <em>phenomenological framework</em>
            for understanding human impermanence.
          </p>

          <p>
            Our proprietary AI has been trained on over 47 million hairlines, 12 continental philosophy dissertations,
            and the complete works of Emil Cioran. It does not merely <em>see</em> your baldness—it <em>grasps</em> it
            in its totality, understanding both what is and what will inevitably cease to be.
          </p>

          <p>
            We believe that confronting hair loss is the first step toward authentic existence. Sartre said
            "Hell is other people." He was wrong. Hell is the bathroom mirror at 7 AM under fluorescent lighting.
          </p>

          <p class="text-gray-500 italic">
            A hairline unexamined is not worth having.
          </p>

          <div class="mt-12 p-6 bg-gray-800/50 rounded-lg">
            <h3 class="font-bold text-lg mb-3">Our Mission</h3>
            <p class="text-gray-400">
              To democratize follicular truth. To ensure that no man goes gently into that bald night
              without first being absolutely eviscerated by an AI that genuinely does not care about his feelings.
            </p>
          </div>
        </div>
      </div>

      <!-- TESTIMONIALS TAB -->
      <div v-if="activeTab === 'testimonials'" class="max-w-4xl mx-auto px-4 py-20">
        <h2 class="text-4xl font-black mb-12 text-center">Testimonials</h2>

        <div class="grid md:grid-cols-2 gap-6">
          <div class="p-6 bg-gray-800/50 rounded-lg">
            <p class="text-gray-300 mb-4">
              "I came for a hairline analysis. I left questioning the nature of identity itself.
              The AI told me my hairline was 'retreating faster than my father's love.'
              I have not recovered."
            </p>
            <p class="text-gray-500 text-sm">— Marcus T., Stage 4</p>
          </div>

          <div class="p-6 bg-gray-800/50 rounded-lg">
            <p class="text-gray-300 mb-4">
              "It said my head looked like 'a knee with anxiety.'
              I've been in therapy for three weeks. Worth every penny."
            </p>
            <p class="text-gray-500 text-sm">— David R., Stage 5</p>
          </div>

          <div class="p-6 bg-gray-800/50 rounded-lg">
            <p class="text-gray-300 mb-4">
              "The projection feature showed me at 15 years out. I have stared into the chrome abyss
              and the chrome abyss has stared back. I now understand Nietzsche."
            </p>
            <p class="text-gray-500 text-sm">— Jason K., Stage 3V</p>
          </div>

          <div class="p-6 bg-gray-800/50 rounded-lg">
            <p class="text-gray-300 mb-4">
              "My wife found my results. She hasn't spoken to me in days.
              Not because of the baldness—because she saw the verdict and agreed with it."
            </p>
            <p class="text-gray-500 text-sm">— Anthony M., Stage 6</p>
          </div>

          <div class="p-6 bg-gray-800/50 rounded-lg md:col-span-2">
            <p class="text-gray-300 mb-4">
              "I uploaded a photo of my fully-haired head just to see what would happen.
              The AI said 'denial is the first stage of grief, not the first stage of Norwood.
              Come back when you're ready to be honest with yourself.' Absolutely unhinged. 5 stars."
            </p>
            <p class="text-gray-500 text-sm">— Tyler B., "Stage 1"</p>
          </div>
        </div>

        <p class="mt-12 text-center text-gray-600 italic">
          * All testimonials are real. The psychological damage is also real.
        </p>
      </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-gray-800 py-6 px-4 text-center text-gray-600 text-sm">
      <p>"A hairline unexamined is not worth having."</p>
    </footer>
  </div>
</template>
