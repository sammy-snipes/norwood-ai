<script setup>
import { ref, onMounted, computed } from 'vue'

const emit = defineEmits(['close', 'donate'])

const canvasRef = ref(null)
const isDrawing = ref(false)
const mode = ref('erase') // 'erase' or 'hair'
const erasedPercent = ref(0)
const feedback = ref(null)

// Target range for Norwood 3 (35-45% erased)
const targetMin = 35
const targetMax = 45

let ctx = null

onMounted(() => {
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')
  drawHead()
  calculateErased()
})

const drawHead = () => {
  const canvas = canvasRef.value
  ctx.fillStyle = '#1f2937'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Face
  ctx.fillStyle = '#d4a574'
  ctx.beginPath()
  ctx.ellipse(150, 140, 70, 85, 0, 0, Math.PI * 2)
  ctx.fill()

  // Full head of hair (low hairline - lots to work with)
  ctx.fillStyle = '#4a3728'

  // Main hair mass
  ctx.beginPath()
  ctx.ellipse(150, 70, 80, 55, 0, 0, Math.PI, true)
  ctx.fill()

  // Lower hairline
  ctx.beginPath()
  ctx.ellipse(150, 95, 72, 40, 0, 0, Math.PI, true)
  ctx.fill()

  // Side hair
  ctx.fillRect(72, 75, 18, 70)
  ctx.fillRect(210, 75, 18, 70)

  // Eyes
  ctx.fillStyle = '#1f2937'
  ctx.beginPath()
  ctx.ellipse(125, 130, 8, 5, 0, 0, Math.PI * 2)
  ctx.ellipse(175, 130, 8, 5, 0, 0, Math.PI * 2)
  ctx.fill()

  // Stoic mouth
  ctx.strokeStyle = '#8b6914'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(130, 170)
  ctx.lineTo(170, 170)
  ctx.stroke()
}

const startDraw = (e) => {
  isDrawing.value = true
  draw(e)
}

const stopDraw = () => {
  isDrawing.value = false
  calculateErased()
  updateFeedback()
}

const draw = (e) => {
  if (!isDrawing.value) return

  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left
  const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top

  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const canvasX = x * scaleX
  const canvasY = y * scaleY

  // Only draw in hair zone (top of head, not sides)
  if (canvasY < 110 && canvasY > 15 && canvasX > 90 && canvasX < 210) {
    if (mode.value === 'erase') {
      ctx.fillStyle = '#d4a574' // Skin
    } else {
      ctx.fillStyle = '#4a3728' // Hair
    }
    ctx.beginPath()
    ctx.arc(canvasX, canvasY, 12, 0, Math.PI * 2)
    ctx.fill()
  }
}

const calculateErased = () => {
  const imageData = ctx.getImageData(90, 15, 120, 95)
  const data = imageData.data
  let skinPixels = 0
  let totalPixels = 0

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i]
    const g = data[i + 1]
    const b = data[i + 2]
    totalPixels++

    if (r > 180 && g > 140 && b > 90) {
      skinPixels++
    }
  }

  erasedPercent.value = Math.round((skinPixels / totalPixels) * 100)
}

const tooMuchHair = computed(() => erasedPercent.value < targetMin)
const tooLittleHair = computed(() => erasedPercent.value > targetMax)
const justRight = computed(() => erasedPercent.value >= targetMin && erasedPercent.value <= targetMax)

const updateFeedback = () => {
  if (tooMuchHair.value) {
    const msgs = [
      "Still too much hair.",
      "Not quite. The temples.",
      "A Norwood 3 has less.",
      "Keep going. Time always does.",
      "The hairline recedes further than this.",
    ]
    feedback.value = msgs[Math.floor(Math.random() * msgs.length)]
  } else if (tooLittleHair.value) {
    const msgs = [
      "Too much. He's not there yet.",
      "Whoa. Bring some back.",
      "That's a 4 or 5. Dial it back.",
      "You've gone too far. As we all eventually do.",
      "Overcorrection. A common mistake.",
    ]
    feedback.value = msgs[Math.floor(Math.random() * msgs.length)]
  } else {
    feedback.value = "Correct. You may proceed."
  }
}

const handleSubmit = () => {
  if (justRight.value) {
    emit('close')
  }
}
</script>

<template>
  <div class="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
    <div class="bg-gray-800 border border-gray-700 rounded-lg p-4 w-80 text-center">
      <div class="flex items-center gap-2 mb-3">
        <div class="w-5 h-5 bg-blue-500 rounded flex items-center justify-center">
          <span class="text-white text-xs font-bold">✓</span>
        </div>
        <span class="text-gray-300 text-xs">Verify you're human</span>
      </div>

      <p class="text-gray-400 text-xs mb-3">
        Adjust the subject to Norwood 3
      </p>

      <!-- Mode toggle -->
      <div class="flex gap-1 mb-2">
        <button
          @click="mode = 'erase'"
          class="flex-1 px-2 py-1 text-xs rounded transition-colors"
          :class="mode === 'erase'
            ? 'bg-purple-600 text-white'
            : 'bg-gray-700 text-gray-400 hover:bg-gray-600'"
        >
          Erase
        </button>
        <button
          @click="mode = 'hair'"
          class="flex-1 px-2 py-1 text-xs rounded transition-colors"
          :class="mode === 'hair'
            ? 'bg-purple-600 text-white'
            : 'bg-gray-700 text-gray-400 hover:bg-gray-600'"
        >
          Hair
        </button>
      </div>

      <canvas
        ref="canvasRef"
        width="300"
        height="220"
        class="w-full rounded border border-gray-600 cursor-crosshair mb-3"
        @mousedown="startDraw"
        @mouseup="stopDraw"
        @mouseleave="stopDraw"
        @mousemove="draw"
        @touchstart.prevent="startDraw"
        @touchend="stopDraw"
        @touchmove.prevent="draw"
      />

      <p
        v-if="feedback"
        class="text-xs mb-3"
        :class="justRight ? 'text-green-400' : 'text-gray-400'"
      >
        {{ feedback }}
      </p>

      <button
        @click="handleSubmit"
        :disabled="!justRight"
        class="w-full px-3 py-1.5 text-xs rounded transition-colors"
        :class="justRight
          ? 'bg-purple-600 hover:bg-purple-500 text-white'
          : 'bg-gray-700 text-gray-500 cursor-not-allowed'"
      >
        Continue
      </button>
    </div>
  </div>
</template>
