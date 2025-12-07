<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['close', 'donate'])

const authStore = useAuthStore()
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

// Donation state
const amounts = [10, 50, 500, 5000]
const selectedAmount = ref(10)
const customAmount = ref('')
const loading = ref(false)
const error = ref(null)

// Tic tac toe state
const showTicTacToe = ref(false)
const board = ref(Array(9).fill(null)) // null, 'X' (site), 'O' (user)
const gameOver = ref(false)
const gameMessage = ref('')
const userWon = ref(false)

const actualAmount = () => {
  if (customAmount.value) {
    const parsed = parseInt(customAmount.value)
    return parsed > 0 ? parsed : null
  }
  return selectedAmount.value
}

const selectAmount = (amount) => {
  selectedAmount.value = amount
  customAmount.value = ''
}

const handleDonate = async () => {
  const amount = actualAmount()
  if (!amount || amount < 1) {
    error.value = 'Please select an amount'
    return
  }

  loading.value = true
  error.value = null

  try {
    const response = await fetch(`${API_URL}/api/payments/create-donation`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ amount_dollars: amount })
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to create checkout')
    }

    const data = await response.json()
    window.open(data.checkout_url, '_blank')
    emit('donate')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// Tic tac toe logic
const winPatterns = [
  [0, 1, 2], [3, 4, 5], [6, 7, 8], // rows
  [0, 3, 6], [1, 4, 7], [2, 5, 8], // cols
  [0, 4, 8], [2, 4, 6] // diagonals
]

const checkWinner = (b) => {
  for (const pattern of winPatterns) {
    const [a, b1, c] = pattern
    if (b[a] && b[a] === b[b1] && b[a] === b[c]) {
      return b[a]
    }
  }
  return null
}

const isBoardFull = (b) => b.every(cell => cell !== null)

const getEmptyCells = (b) => b.map((cell, i) => cell === null ? i : null).filter(i => i !== null)

const siteMove = () => {
  const empty = getEmptyCells(board.value)
  if (empty.length === 0) return

  // Random move
  const idx = empty[Math.floor(Math.random() * empty.length)]
  board.value[idx] = 'X'

  const winner = checkWinner(board.value)
  if (winner === 'X') {
    gameOver.value = true
    gameMessage.value = "You lose! Idiot! You can't close this popup until you win."
    userWon.value = false
  } else if (isBoardFull(board.value)) {
    gameOver.value = true
    gameMessage.value = "It's a draw. Try again, coward."
    userWon.value = false
  }
}

const userMove = (idx) => {
  if (board.value[idx] !== null || gameOver.value) return

  board.value[idx] = 'O'

  const winner = checkWinner(board.value)
  if (winner === 'O') {
    gameOver.value = true
    gameMessage.value = "You won. Closing..."
    userWon.value = true
    setTimeout(() => emit('close'), 1500)
    return
  }

  if (isBoardFull(board.value)) {
    gameOver.value = true
    gameMessage.value = "It's a draw. Try again, coward."
    userWon.value = false
    return
  }

  // Site's turn
  setTimeout(siteMove, 300)
}

const startTicTacToe = () => {
  showTicTacToe.value = true
  board.value = Array(9).fill(null)
  gameOver.value = false
  gameMessage.value = ''
  userWon.value = false

  // Site goes first
  setTimeout(siteMove, 300)
}

const resetGame = () => {
  board.value = Array(9).fill(null)
  gameOver.value = false
  gameMessage.value = ''
  userWon.value = false

  // Site goes first
  setTimeout(siteMove, 300)
}

const getCellDisplay = (cell) => {
  if (cell === 'X') return 'X'
  if (cell === 'O') return 'O'
  return ''
}
</script>

<template>
  <div class="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
    <div class="bg-gray-800 border border-gray-700 rounded-lg p-5 w-80">

      <!-- Donation View -->
      <template v-if="!showTicTacToe">
        <h2 class="text-sm font-medium text-gray-300 mb-1">I need a hair transplant</h2>
        <p class="text-xs text-gray-500 mb-4">My real job doesn't pay enough. Help a brother out.</p>

        <!-- Amount selection -->
        <div class="grid grid-cols-4 gap-2 mb-3">
          <button
            v-for="amount in amounts"
            :key="amount"
            @click="selectAmount(amount)"
            class="py-2 text-sm rounded transition-colors"
            :class="selectedAmount === amount && !customAmount
              ? 'bg-purple-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
          >
            ${{ amount.toLocaleString() }}
          </button>
        </div>

        <!-- Custom amount -->
        <div class="mb-4">
          <input
            v-model="customAmount"
            type="number"
            min="1"
            placeholder="Custom amount"
            class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
            @focus="selectedAmount = null"
          />
        </div>

        <!-- Error -->
        <div v-if="error" class="mb-3 text-xs text-red-400">
          {{ error }}
        </div>

        <!-- Buttons -->
        <div class="flex gap-2">
          <button
            @click="handleDonate"
            :disabled="loading || !actualAmount()"
            class="flex-1 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm rounded transition-colors"
          >
            <span v-if="loading">Processing...</span>
            <span v-else>Donate{{ actualAmount() ? ` $${actualAmount()}` : '' }}</span>
          </button>
          <button
            @click="startTicTacToe"
            :disabled="loading"
            class="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded transition-colors"
          >
            Later
          </button>
        </div>

        <p class="mt-3 text-xs text-gray-500 text-center">
          This is a donation, not a Sage Mode upgrade.
        </p>
      </template>

      <!-- Tic Tac Toe View -->
      <template v-else>
        <h2 class="text-sm font-medium text-gray-300 mb-2">Beat me to close this popup</h2>
        <p class="text-xs text-gray-500 mb-4">You're O. Good luck.</p>

        <!-- Board -->
        <div class="grid grid-cols-3 gap-1 mb-4">
          <button
            v-for="(cell, idx) in board"
            :key="idx"
            @click="userMove(idx)"
            :disabled="cell !== null || gameOver"
            class="aspect-square bg-gray-700 hover:bg-gray-600 disabled:hover:bg-gray-700 rounded flex items-center justify-center text-2xl font-bold transition-colors"
            :class="{
              'text-red-400': cell === 'X',
              'text-green-400': cell === 'O',
              'cursor-not-allowed': cell !== null || gameOver
            }"
          >
            {{ getCellDisplay(cell) }}
          </button>
        </div>

        <!-- Game message -->
        <div v-if="gameMessage" class="mb-4 text-center">
          <p
            class="text-sm"
            :class="userWon ? 'text-green-400' : 'text-red-400'"
          >
            {{ gameMessage }}
          </p>
        </div>

        <!-- Play again button -->
        <button
          v-if="gameOver && !userWon"
          @click="resetGame"
          class="w-full py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded transition-colors"
        >
          Try Again
        </button>
      </template>

    </div>
  </div>
</template>
