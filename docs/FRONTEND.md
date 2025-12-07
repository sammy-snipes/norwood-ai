# Frontend Development Guide

## Project Structure

```
frontend/src/
├── App.vue                 # Root component
├── main.js                 # App initialization
├── style.css               # Global styles (Tailwind)
├── router/index.js         # Routes and auth guards
├── stores/
│   ├── auth.js             # Authentication state
│   └── tasks.js            # Task polling state
├── views/                  # Page components
└── components/             # Reusable components
```

## Tech Stack

- Vue 3 with Composition API (`<script setup>`)
- Pinia for state management
- Vue Router 4
- Tailwind CSS
- Vite

## Key Patterns

### 1. Authentication

```javascript
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

// Check if logged in
if (authStore.isAuthenticated) { ... }

// Get user data
authStore.user?.name
authStore.user?.is_premium
authStore.user?.is_admin
authStore.user?.options?.completed_captcha

// Refresh user data from backend
await authStore.fetchUser()
```

### 2. API Calls

```javascript
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

try {
  const res = await fetch(`${API_URL}/api/endpoint`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${authStore.token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ data })
  })

  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Request failed')
  }

  const data = await res.json()
  // handle success
} catch (err) {
  error.value = err.message
}
```

### 3. Task Polling

For async backend operations (Celery tasks):

```javascript
import { useTaskStore } from '../stores/tasks'

const taskStore = useTaskStore()

// Submit task and register for polling
const res = await fetch(`${API_URL}/analyze`, { ... })
const data = await res.json()

taskStore.addTask(
  data.task_id,
  'my-context',           // Context name for grouping
  { someMetadata: 123 },  // Passed to callback
  handleTaskComplete      // Called when done
)

// Callback receives result
function handleTaskComplete({ success, result, error, metadata }) {
  if (success) {
    // result contains task output
  } else {
    // error contains error message
  }
}
```

Restore state on component mount:

```javascript
onMounted(() => {
  // Check if we have pending tasks
  if (taskStore.hasPendingTasks('my-context')) {
    isLoading.value = true
    taskStore.updateCallback('my-context', handleTaskComplete)
  }

  // Restore last active item
  const lastId = taskStore.getLastActive('my-context')
  if (lastId) {
    selectItem(lastId)
  }
})

// Save active item when selecting
taskStore.setLastActive('my-context', itemId)
```

### 4. Premium Access Control

```javascript
const hasUnlimited = computed(() => {
  return authStore.user?.is_admin || authStore.user?.is_premium
})

// In template
<div v-if="!hasUnlimited">
  <!-- Paywall / upgrade prompt -->
</div>
<div v-else>
  <!-- Premium content -->
</div>
```

### 5. Component Structure

```vue
<script setup>
// 1. Imports
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'

// 2. Store initialization
const authStore = useAuthStore()

// 3. State
const isLoading = ref(false)
const error = ref(null)
const result = ref(null)

// 4. Computed
const canSubmit = computed(() => !isLoading.value && hasData.value)

// 5. Methods
const fetchData = async () => { ... }
const handleSubmit = async () => { ... }

// 6. Lifecycle
onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <!-- Content -->
  </div>
</template>
```

### 6. Modals

Full-screen overlay pattern:

```vue
<template>
  <div class="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
    <div class="bg-gray-800 border border-gray-700 rounded-lg p-5 w-80">
      <!-- Modal content -->
      <button @click="emit('close')">Close</button>
    </div>
  </div>
</template>
```

### 7. Loading States

```vue
<button
  @click="submit"
  :disabled="isLoading"
  class="... disabled:opacity-50 disabled:cursor-not-allowed"
>
  <span v-if="isLoading">Processing...</span>
  <span v-else>Submit</span>
</button>

<!-- Spinner -->
<div class="w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
```

### 8. Error Display

```vue
<div v-if="error" class="p-3 bg-red-900/30 border border-red-700 rounded text-red-400 text-sm">
  {{ error }}
</div>
```

## Naming Conventions

- **Files**: PascalCase for Vue (`MyComponent.vue`), camelCase for JS (`myStore.js`)
- **Variables**: camelCase (`isLoading`, `selectedFile`)
- **Functions**: camelCase, prefix with `handle` for events (`handleSubmit`)
- **Booleans**: prefix with `is`, `has`, `can`, `show` (`isLoading`, `hasUnlimited`)
- **CSS**: Tailwind utilities, minimal custom CSS

## Common Tailwind Classes

**Layout**:
- `min-h-screen bg-gray-900 text-white` - Page wrapper
- `flex flex-col` / `flex items-center justify-center`
- `max-w-xl mx-auto px-4 py-8` - Centered content

**Cards**:
- `bg-gray-800 border border-gray-700 rounded-lg p-4`
- `bg-gray-800/50` - Semi-transparent

**Text**:
- `text-gray-400` - Secondary text
- `text-gray-500` - Muted text
- `text-xs` / `text-sm` - Small text

**Buttons**:
- Primary: `bg-purple-600 hover:bg-purple-500 text-white`
- Secondary: `bg-gray-700 hover:bg-gray-600 text-gray-300`
- Disabled: `disabled:opacity-50 disabled:cursor-not-allowed`

**States**:
- `hover:bg-gray-600`
- `transition-colors`
- `animate-spin` / `animate-pulse`

## Adding a New View

1. Create `views/MyFeature.vue`
2. Add route in `router/index.js`:
   ```javascript
   {
     path: '/my-feature',
     name: 'myFeature',
     component: () => import('../views/MyFeature.vue'),
     meta: { requiresAuth: true }
   }
   ```
3. Add nav link in `AppHeader.vue` if needed

## Adding a New Component

1. Create `components/MyComponent.vue`
2. Define props and emits:
   ```javascript
   const props = defineProps({
     items: Array,
     selectedId: String
   })

   const emit = defineEmits(['select', 'delete'])
   ```
3. Import and use in parent view

## File Uploads

```javascript
// From file input
const onFileSelect = (e) => {
  const file = e.target.files[0]
  previewUrl.value = URL.createObjectURL(file)
  selectedFile.value = file
}

// Submit as FormData
const formData = new FormData()
formData.append('file', selectedFile.value)

await fetch(url, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData  // No Content-Type header for FormData
})

// Or as base64 JSON
const reader = new FileReader()
reader.onload = async () => {
  const base64 = reader.result.split(',')[1]
  await fetch(url, {
    headers: { 'Content-Type': 'application/json', ... },
    body: JSON.stringify({ image: base64, media_type: file.type })
  })
}
reader.readAsDataURL(file)
```
