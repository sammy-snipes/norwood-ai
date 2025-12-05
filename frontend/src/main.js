import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Initialize auth store before mounting
const authStore = useAuthStore()
authStore.init().then(() => {
  // If authenticated and on landing page, redirect to analyze
  if (authStore.isAuthenticated && window.location.pathname === '/') {
    router.replace('/analyze')
  }
  app.mount('#app')
})
