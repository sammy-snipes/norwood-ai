<script setup>
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <div v-if="authStore.loading" class="min-h-screen bg-gray-900 flex items-center justify-center">
    <div class="text-white text-xl">Loading...</div>
  </div>
  <router-view v-else />
</template>
