<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import AppHeader from '../components/AppHeader.vue'

// Game constants
const SIZE = 4
const WIN_VALUE = 7 // Norwood 7 to win

// Direction vectors (matching original 2048)
// y increases downward (y=0 is top row, y=3 is bottom row)
// up means moving toward y=0, so y decreases (y: -1)
// down means moving toward y=3, so y increases (y: +1)
const VECTORS = {
  up: { x: 0, y: -1 },
  right: { x: 1, y: 0 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 }
}

// Game state
const grid = ref([])
const score = ref(0)
const bestScore = ref(parseInt(localStorage.getItem('norwood2048_best') || '0'))
const gameOver = ref(false)
const gameWon = ref(false)
const keepPlaying = ref(false)
const showDonateToast = ref(false)
const isMoving = ref(false)

// Tile tracking for animations
let tileId = 0
const tiles = ref([])

// Touch handling
const touchStartX = ref(0)
const touchStartY = ref(0)

// Norwood images mapping (value 0-7)
const getNorwoodImage = (value) => {
  if (value === null || value === undefined) return null
  return `/img/2048/norwood-${value}.jpg`
}

// Tile background colors based on Norwood level
const getTileClasses = (value) => {
  const colors = {
    0: 'bg-emerald-800/90 border-emerald-600',
    1: 'bg-emerald-700/90 border-emerald-500',
    2: 'bg-yellow-700/90 border-yellow-500',
    3: 'bg-amber-700/90 border-amber-500',
    4: 'bg-orange-700/90 border-orange-500',
    5: 'bg-orange-600/90 border-orange-400',
    6: 'bg-red-700/90 border-red-500',
    7: 'bg-red-600/90 border-red-400 ring-2 ring-yellow-400'
  }
  return colors[value] || 'bg-gray-700 border-gray-600'
}

// Initialize empty grid
const createGrid = () => {
  const g = []
  for (let y = 0; y < SIZE; y++) {
    g[y] = []
    for (let x = 0; x < SIZE; x++) {
      g[y][x] = null
    }
  }
  return g
}

// Get all empty cells
const getEmptyCells = () => {
  const empty = []
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      if (!grid.value[y][x]) {
        empty.push({ x, y })
      }
    }
  }
  return empty
}

// Add a random tile
const addRandomTile = () => {
  const empty = getEmptyCells()
  if (empty.length === 0) return null

  const cell = empty[Math.floor(Math.random() * empty.length)]
  const value = Math.random() < 0.9 ? 0 : 1

  const tile = {
    id: ++tileId,
    x: cell.x,
    y: cell.y,
    value,
    isNew: true,
    mergedFrom: null
  }

  grid.value[cell.y][cell.x] = tile
  tiles.value.push(tile)

  // Remove isNew flag after animation
  setTimeout(() => {
    tile.isNew = false
  }, 150)

  return tile
}

// Check if position is within grid
const withinBounds = (x, y) => {
  return x >= 0 && x < SIZE && y >= 0 && y < SIZE
}

// Get cell content
const cellContent = (x, y) => {
  if (withinBounds(x, y)) {
    return grid.value[y][x]
  }
  return null
}

// Check if cell is available
const cellAvailable = (x, y) => {
  return withinBounds(x, y) && !cellContent(x, y)
}

// Build traversal order based on direction
// We need to process tiles farthest from the direction of movement first
const buildTraversals = (vector) => {
  const traversals = { x: [], y: [] }

  for (let i = 0; i < SIZE; i++) {
    traversals.x.push(i)
    traversals.y.push(i)
  }

  // When moving right (vector.x = 1), process from right to left (3,2,1,0)
  // When moving down (vector.y = 1), process from bottom to top (3,2,1,0)
  if (vector.x === 1) traversals.x.reverse()
  if (vector.y === 1) traversals.y.reverse()

  return traversals
}

// Find farthest position in direction
const findFarthestPosition = (x, y, vector) => {
  let prevX = x
  let prevY = y
  let nextX = x + vector.x
  let nextY = y + vector.y

  while (withinBounds(nextX, nextY) && !cellContent(nextX, nextY)) {
    prevX = nextX
    prevY = nextY
    nextX += vector.x
    nextY += vector.y
  }

  return {
    farthest: { x: prevX, y: prevY },
    next: withinBounds(nextX, nextY) ? { x: nextX, y: nextY } : null
  }
}

// Move tiles in direction
const move = (direction) => {
  if (gameOver.value || isMoving.value) return
  if (gameWon.value && !keepPlaying.value) return

  const vector = VECTORS[direction]
  const traversals = buildTraversals(vector)
  let moved = false
  let scoreAdd = 0

  // Clear merge flags
  tiles.value.forEach(tile => {
    tile.mergedFrom = null
  })

  // Traverse grid
  traversals.y.forEach(y => {
    traversals.x.forEach(x => {
      const tile = cellContent(x, y)
      if (!tile) return

      const positions = findFarthestPosition(x, y, vector)
      const next = positions.next ? cellContent(positions.next.x, positions.next.y) : null

      // Check if we can merge with adjacent tile
      if (next && next.value === tile.value && !next.mergedFrom && tile.value < WIN_VALUE) {
        // Merge tiles
        const merged = {
          id: ++tileId,
          x: positions.next.x,
          y: positions.next.y,
          value: tile.value + 1,
          isNew: false,
          mergedFrom: [tile, next]
        }

        // Update grid
        grid.value[y][x] = null
        grid.value[positions.next.y][positions.next.x] = merged

        // Update tile positions for animation
        tile.x = positions.next.x
        tile.y = positions.next.y

        // Remove old tiles, add merged
        tiles.value = tiles.value.filter(t => t.id !== tile.id && t.id !== next.id)
        tiles.value.push(merged)

        // Update score
        scoreAdd += Math.pow(2, merged.value + 1)

        // Check win condition
        if (merged.value === WIN_VALUE && !keepPlaying.value) {
          gameWon.value = true
        }

        moved = true
      } else {
        // Just move tile
        const dest = positions.farthest
        if (x !== dest.x || y !== dest.y) {
          grid.value[y][x] = null
          grid.value[dest.y][dest.x] = tile
          tile.x = dest.x
          tile.y = dest.y
          moved = true
        }
      }
    })
  })

  if (moved) {
    score.value += scoreAdd

    if (score.value > bestScore.value) {
      bestScore.value = score.value
      localStorage.setItem('norwood2048_best', bestScore.value.toString())
    }

    // Add new tile after brief delay
    isMoving.value = true
    setTimeout(() => {
      addRandomTile()
      isMoving.value = false

      // Check game over
      if (!movesAvailable()) {
        gameOver.value = true
      }
    }, 100)
  }
}

// Check if any moves are available
const movesAvailable = () => {
  // Check for empty cells
  if (getEmptyCells().length > 0) return true

  // Check for possible merges
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const tile = cellContent(x, y)
      if (!tile) continue

      // Check adjacent cells
      for (const dir of Object.values(VECTORS)) {
        const nextX = x + dir.x
        const nextY = y + dir.y
        const next = cellContent(nextX, nextY)
        if (next && next.value === tile.value) {
          return true
        }
      }
    }
  }

  return false
}

// Start new game
const newGame = () => {
  grid.value = createGrid()
  tiles.value = []
  score.value = 0
  gameOver.value = false
  gameWon.value = false
  keepPlaying.value = false
  tileId = 0

  addRandomTile()
  addRandomTile()
}

// Continue playing after win
const continueGame = () => {
  keepPlaying.value = true
  gameWon.value = false
}

// Keyboard handler
const handleKeydown = (e) => {
  const keyMap = {
    ArrowUp: 'up',
    ArrowDown: 'down',
    ArrowLeft: 'left',
    ArrowRight: 'right',
    w: 'up',
    s: 'down',
    a: 'left',
    d: 'right'
  }

  const direction = keyMap[e.key]
  if (direction) {
    e.preventDefault()
    move(direction)
  }
}

// Touch handlers for swipe
const handleTouchStart = (e) => {
  touchStartX.value = e.touches[0].clientX
  touchStartY.value = e.touches[0].clientY
}

const handleTouchEnd = (e) => {
  const deltaX = e.changedTouches[0].clientX - touchStartX.value
  const deltaY = e.changedTouches[0].clientY - touchStartY.value
  const minSwipe = 50

  const absDeltaX = Math.abs(deltaX)
  const absDeltaY = Math.abs(deltaY)

  if (Math.max(absDeltaX, absDeltaY) < minSwipe) return

  if (absDeltaX > absDeltaY) {
    move(deltaX > 0 ? 'right' : 'left')
  } else {
    move(deltaY > 0 ? 'down' : 'up')
  }
}

// Tile position style
const getTileStyle = (tile) => {
  const cellSize = 100 / SIZE
  return {
    left: `${tile.x * cellSize}%`,
    top: `${tile.y * cellSize}%`,
    width: `${cellSize}%`,
    height: `${cellSize}%`
  }
}

onMounted(() => {
  newGame()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white flex flex-col">
    <AppHeader @donate="showDonateToast = true" />

    <main class="flex-1 flex flex-col items-center justify-center p-4">
      <div class="w-full max-w-md">
        <!-- Title and scores -->
        <div class="flex items-center justify-between mb-4">
          <div>
            <h1 class="text-2xl font-bold text-gray-200">Norwood 2048</h1>
            <p class="text-xs text-gray-500">Combine heads to reach Norwood 7!</p>
          </div>
          <div class="flex gap-2">
            <div class="bg-gray-800 rounded px-3 py-1.5 text-center min-w-[70px]">
              <div class="text-[10px] text-gray-500 uppercase tracking-wide">Score</div>
              <div class="text-lg font-bold text-gray-200">{{ score }}</div>
            </div>
            <div class="bg-gray-800 rounded px-3 py-1.5 text-center min-w-[70px]">
              <div class="text-[10px] text-gray-500 uppercase tracking-wide">Best</div>
              <div class="text-lg font-bold text-gray-200">{{ bestScore }}</div>
            </div>
          </div>
        </div>

        <!-- New game button -->
        <div class="flex justify-end mb-2">
          <button
            @click="newGame"
            class="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
          >
            New Game
          </button>
        </div>

        <!-- Game grid -->
        <div
          class="relative bg-gray-800 rounded-lg p-2 select-none"
          @touchstart.prevent="handleTouchStart"
          @touchend.prevent="handleTouchEnd"
        >
          <!-- Aspect ratio container -->
          <div class="relative w-full" style="padding-bottom: 100%;">
            <!-- Grid background cells -->
            <div class="absolute inset-0 grid grid-cols-4 gap-2">
              <template v-for="i in 16" :key="'bg-' + i">
                <div class="bg-gray-700/60 rounded-lg"></div>
              </template>
            </div>

            <!-- Tile container -->
            <div class="absolute inset-0 p-0">
              <TransitionGroup name="tile">
                <div
                  v-for="tile in tiles"
                  :key="tile.id"
                  class="absolute p-1 transition-all duration-100 ease-out"
                  :style="getTileStyle(tile)"
                >
                  <div
                    class="w-full h-full rounded-lg border-2 flex items-center justify-center overflow-hidden"
                    :class="[
                      getTileClasses(tile.value),
                      tile.isNew ? 'animate-pop' : '',
                      tile.mergedFrom ? 'animate-merge' : ''
                    ]"
                  >
                    <img
                      :src="getNorwoodImage(tile.value)"
                      :alt="'Norwood ' + tile.value"
                      class="w-full h-full object-cover"
                      draggable="false"
                    />
                  </div>
                </div>
              </TransitionGroup>
            </div>
          </div>

          <!-- Game over overlay -->
          <div
            v-if="gameOver"
            class="absolute inset-0 bg-gray-900/85 rounded-lg flex flex-col items-center justify-center z-10"
          >
            <h2 class="text-2xl font-bold text-gray-200 mb-2">Game Over!</h2>
            <p class="text-gray-400 mb-4">Final Score: {{ score }}</p>
            <button
              @click="newGame"
              class="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors font-medium"
            >
              Try Again
            </button>
          </div>

          <!-- Win overlay -->
          <div
            v-if="gameWon && !keepPlaying"
            class="absolute inset-0 bg-gray-900/85 rounded-lg flex flex-col items-center justify-center z-10"
          >
            <h2 class="text-2xl font-bold text-yellow-400 mb-2">You Win!</h2>
            <p class="text-gray-400 mb-1">You reached Norwood 7!</p>
            <p class="text-gray-500 text-sm mb-4">Score: {{ score }}</p>
            <div class="flex gap-3">
              <button
                @click="continueGame"
                class="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Keep Going
              </button>
              <button
                @click="newGame"
                class="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors font-medium"
              >
                New Game
              </button>
            </div>
          </div>
        </div>

        <!-- Instructions -->
        <div class="mt-4 text-center text-xs text-gray-500">
          <p class="mb-1">Use WASD or arrow keys to move tiles</p>
          <p>Swipe on mobile. Combine matching levels!</p>
        </div>

        <!-- Norwood scale reference -->
        <div class="mt-6 bg-gray-800 rounded-lg p-3">
          <h3 class="text-xs text-gray-400 mb-2 text-center">Norwood Scale</h3>
          <div class="flex justify-between gap-1">
            <template v-for="n in 8" :key="'ref-' + n">
              <div class="flex flex-col items-center flex-1">
                <div class="w-full aspect-square rounded overflow-hidden border border-gray-700">
                  <img
                    :src="getNorwoodImage(n - 1)"
                    :alt="'Norwood ' + (n - 1)"
                    class="w-full h-full object-cover"
                  />
                </div>
                <span class="text-[10px] text-gray-500 mt-1">{{ n - 1 }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Tile animations */
@keyframes pop {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes merge {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.15);
  }
  100% {
    transform: scale(1);
  }
}

.animate-pop {
  animation: pop 150ms ease-out;
}

.animate-merge {
  animation: merge 150ms ease-out;
}

/* TransitionGroup animations */
.tile-move {
  transition: all 100ms ease-out;
}
</style>
