import { createRouter, createWebHistory } from 'vue-router'

// Import views
import DashboardView from '../views/DashboardView.vue'

// Define routes
const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: DashboardView
  },
  {
    path: '/database',
    name: 'database',
    component: () => import('../views/DatabaseView.vue')
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('../views/ChatView.vue')
  },
  {
    path: '/upload',
    name: 'upload',
    component: () => import('../views/UploadView.vue')
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: () => import('../views/AnalysisView.vue')
  },
  {
    path: '/provider-analysis/:providerName',
    name: 'provider-analysis',
    component: () => import('../views/UniversalProviderAnalysisView.vue'),
    props: true
  },
      {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue')
    },
    {
      path: '/operations',
      name: 'operations',
      component: () => import('../views/OperationsView.vue')
    },
    {
      path: '/ada-settings',
      name: 'ada-settings',
      component: () => import('../views/AdaSettingsView.vue')
    }
]

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router