import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import Landing from '../views/Landing.vue'
import Analyze from '../views/Analyze.vue'
import Settings from '../views/Settings.vue'
import CheckoutSuccess from '../views/CheckoutSuccess.vue'
import CheckoutCancel from '../views/CheckoutCancel.vue'

const routes = [
  {
    path: '/',
    name: 'landing',
    component: Landing,
    meta: { requiresAuth: false }
  },
  {
    path: '/analyze',
    name: 'analyze',
    component: Analyze,
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'settings',
    component: Settings,
    meta: { requiresAuth: true }
  },
  {
    path: '/checkout/success',
    name: 'checkout-success',
    component: CheckoutSuccess,
    meta: { requiresAuth: true }
  },
  {
    path: '/checkout/cancel',
    name: 'checkout-cancel',
    component: CheckoutCancel,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Wait for auth to initialize if we have a token but no user yet
  if (authStore.token && !authStore.user && !authStore.loading) {
    await authStore.fetchUser(true)  // Show loading on initial auth check
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to landing if not authenticated
    next({ name: 'landing' })
  } else if (to.name === 'landing' && authStore.isAuthenticated) {
    // Redirect to analyze if already logged in
    next({ name: 'analyze' })
  } else {
    next()
  }
})

export default router
