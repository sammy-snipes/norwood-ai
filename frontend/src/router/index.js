import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import Landing from '../views/Landing.vue'
import Analyze from '../views/Analyze.vue'
import Counseling from '../views/Counseling.vue'
import Certification from '../views/Certification.vue'
import CertificatePublic from '../views/CertificatePublic.vue'
import CockCertification from '../views/CockCertification.vue'
import CockCertificatePublic from '../views/CockCertificatePublic.vue'
import Leaderboard from '../views/Leaderboard.vue'
import Settings from '../views/Settings.vue'
import CheckoutSuccess from '../views/CheckoutSuccess.vue'
import CheckoutCancel from '../views/CheckoutCancel.vue'
import Game2048 from '../views/Game2048.vue'
import Forum from '../views/Forum.vue'
import ForumThread from '../views/ForumThread.vue'

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
    path: '/counseling',
    name: 'counseling',
    component: Counseling,
    meta: { requiresAuth: true }
  },
  {
    path: '/certification',
    name: 'certification',
    component: Certification,
    meta: { requiresAuth: true }
  },
  {
    path: '/cert/:id',
    name: 'certificate-public',
    component: CertificatePublic,
    meta: { requiresAuth: false }
  },
  {
    path: '/cock-certification',
    name: 'cock-certification',
    component: CockCertification,
    meta: { requiresAuth: true }
  },
  {
    path: '/cock/:id',
    name: 'cock-certificate-public',
    component: CockCertificatePublic,
    meta: { requiresAuth: false }
  },
  {
    path: '/leaderboard',
    name: 'leaderboard',
    component: Leaderboard,
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
  },
  {
    path: '/2048',
    name: '2048',
    component: Game2048,
    meta: { requiresAuth: true }
  },
  {
    path: '/forum',
    name: 'forum',
    component: Forum,
    meta: { requiresAuth: true }
  },
  {
    path: '/forum/:threadId',
    name: 'forum-thread',
    component: ForumThread,
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
