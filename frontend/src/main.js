import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { useThemeStore } from './stores/themeStore'

// Get saved theme from localStorage or default to light
const savedTheme = localStorage.getItem('theme') || 'light'

// Helper function to apply theme to HTML element
const applyThemeToDOM = (theme) => {
  document.documentElement.setAttribute('data-theme', theme)
  document.documentElement.setAttribute('data-v-app', '')
}

// Create Vuetify instance
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: savedTheme,
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
          background: '#F5F5F5',
          surface: '#FFFFFF',
        }
      },
      dark: {
        dark: true,
        colors: {
          primary: '#2196F3',
          secondary: '#616161',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
          background: '#121212',
          surface: '#1E1E1E',
        }
      }
    }
  }
})

// Create and mount app
const app = createApp(App)
const pinia = createPinia()

// Add plugins
app.use(pinia)
app.use(router)
app.use(vuetify)

// Initialize theme from store
const themeStore = useThemeStore(pinia)
themeStore.initTheme()

// Apply theme to DOM
applyThemeToDOM(themeStore.currentTheme)

// Mount app
app.mount('#app')