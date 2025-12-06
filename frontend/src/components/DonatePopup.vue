<script setup>
import { ref } from 'vue'

const emit = defineEmits(['close', 'donate'])

const layer = ref(0)

const layers = [
  {
    text: "Have you considered donating?",
    yes: "Yes",
    no: "No"
  },
  {
    text: "Would you like to take a moment to consider donating?",
    yes: "I suppose",
    no: "Not now"
  },
  {
    text: "Do you want to donate?",
    yes: "Fine",
    no: "Still no"
  },
  {
    text: "If you wanted to donate, would you know it?",
    yes: "Probably",
    no: "Uncertain"
  },
  {
    text: "Consider: you clicked 'No' four times. What does that say about you?",
    yes: "Fair point",
    no: "I contain multitudes"
  },
  {
    text: "A man who says 'No' five times is just a man who hasn't said 'Yes' yet.",
    yes: "Compelling",
    no: "Debatable"
  },
  {
    text: "This is the seventh box. There is no eighth.",
    yes: "Donate",
    no: "I don't believe you"
  },
  {
    text: "You were warned.",
    yes: "I deserve this",
    no: "Donate",
    escape: "Leave, and never return"
  }
]

const current = () => layers[layer.value]

const handleYes = () => {
  emit('donate')
}

const handleNo = () => {
  if (layer.value < layers.length - 1) {
    layer.value++
  } else {
    // Layer 8 "no" is also donate
    emit('donate')
  }
}

const handleEscape = () => {
  emit('close')
}
</script>

<template>
  <div class="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
    <div class="bg-gray-800 border border-gray-700 rounded-lg p-4 w-80 text-center">
      <p class="text-gray-300 text-sm mb-4">{{ current().text }}</p>

      <button
        @click="handleYes"
        class="w-full mb-2 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded transition-colors"
      >
        Donate
      </button>

      <div class="flex gap-2">
        <button
          @click="handleYes"
          class="flex-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded transition-colors"
        >
          {{ current().yes }}
        </button>
        <button
          @click="handleNo"
          class="flex-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded transition-colors"
        >
          {{ current().no }}
        </button>
      </div>

      <button
        v-if="current().escape"
        @click="handleEscape"
        class="mt-4 text-xs text-gray-600 hover:text-gray-400 transition-colors"
      >
        {{ current().escape }}
      </button>
    </div>
  </div>
</template>
