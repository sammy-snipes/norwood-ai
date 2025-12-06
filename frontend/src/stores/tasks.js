import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

/**
 * Global task polling store.
 *
 * Tracks all pending Celery tasks across the app and polls them in one loop.
 * When a task completes, it calls the registered callback.
 *
 * Usage:
 *   const taskStore = useTaskStore()
 *   taskStore.addTask(taskId, 'analyze', (result) => {
 *     // handle completion
 *   })
 *
 *   // Check if view has pending tasks (for restoring loading state)
 *   if (taskStore.hasPendingTasks('analyze')) {
 *     isLoading.value = true
 *   }
 */
export const useTaskStore = defineStore('tasks', () => {
  // Map of taskId -> { callback, addedAt, context }
  const pendingTasks = ref({})

  let pollInterval = null
  const POLL_INTERVAL_MS = 1500

  function addTask(taskId, context, onComplete) {
    pendingTasks.value[taskId] = {
      callback: onComplete,
      context,
      addedAt: Date.now()
    }
    startPolling()
  }

  // Check if there are any pending tasks for a given context
  function hasPendingTasks(context) {
    return Object.values(pendingTasks.value).some(t => t.context === context)
  }

  // Get all pending tasks for a context
  function getTasksForContext(context) {
    return Object.entries(pendingTasks.value)
      .filter(([_, t]) => t.context === context)
      .map(([id, t]) => ({ id, ...t }))
  }

  // Update the callback for tasks in a context (used when component remounts)
  function updateCallback(context, newCallback) {
    for (const task of Object.values(pendingTasks.value)) {
      if (task.context === context) {
        task.callback = newCallback
      }
    }
  }

  function removeTask(taskId) {
    delete pendingTasks.value[taskId]
    if (Object.keys(pendingTasks.value).length === 0) {
      stopPolling()
    }
  }

  function startPolling() {
    if (pollInterval) return
    pollInterval = setInterval(pollAllTasks, POLL_INTERVAL_MS)
    // Also poll immediately
    pollAllTasks()
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  async function pollAllTasks() {
    const authStore = useAuthStore()
    const taskIds = Object.keys(pendingTasks.value)

    if (taskIds.length === 0) {
      stopPolling()
      return
    }

    for (const taskId of taskIds) {
      const task = pendingTasks.value[taskId]
      if (!task) continue

      try {
        const res = await fetch(`${API_URL}/tasks/${taskId}`, {
          headers: { 'Authorization': `Bearer ${authStore.token}` }
        })

        if (res.ok) {
          const data = await res.json()

          if (data.status === 'completed' || data.status === 'failed') {
            // Task is done - call callback and remove
            const callback = task.callback
            removeTask(taskId)

            if (callback) {
              callback({
                success: data.status === 'completed',
                result: data.result,
                error: data.error
              })
            }
          }
        }
      } catch (err) {
        console.error(`Failed to poll task ${taskId}:`, err)
      }
    }
  }

  // Clean up on logout or when store is disposed
  function cleanup() {
    stopPolling()
    pendingTasks.value = {}
  }

  return {
    pendingTasks,
    addTask,
    removeTask,
    hasPendingTasks,
    getTasksForContext,
    updateCallback,
    cleanup
  }
})
