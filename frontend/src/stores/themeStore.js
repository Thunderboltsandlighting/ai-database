import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: localStorage.getItem('theme') || 'light',
  }),
  
  getters: {
    isDarkMode: (state) => state.theme === 'dark',
    currentTheme: (state) => state.theme,
  },
  
  actions: {
    setTheme(newTheme) {
      this.theme = newTheme
      localStorage.setItem('theme', newTheme)
      
      // Dynamically set the Vuetify theme
      if (typeof window !== 'undefined') {
        // Update HTML attributes
        document.documentElement.setAttribute('data-theme', newTheme)
        
        // Directly set Vuetify's theme
        const vuetifyApp = document.querySelector('.v-application')
        if (vuetifyApp) {
          vuetifyApp.classList.remove('v-theme--light', 'v-theme--dark')
          vuetifyApp.classList.add(`v-theme--${newTheme}`)
        }
      }
    },
    
    toggleTheme() {
      const newTheme = this.theme === 'light' ? 'dark' : 'light'
      this.setTheme(newTheme)
    },
    
    initTheme() {
      // Apply theme on app initialization
      document.documentElement.setAttribute('data-theme', this.theme)
    }
  }
})