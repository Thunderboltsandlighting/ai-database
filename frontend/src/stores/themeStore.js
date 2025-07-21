import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: localStorage.getItem('theme') || 'light',
  }),
  
  getters: {
    isDarkMode: (state) => {
      if (state.theme === 'system') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches
      }
      return state.theme === 'dark'
    },
    currentTheme: (state) => state.theme,
    effectiveTheme: (state) => {
      if (state.theme === 'system') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      }
      return state.theme
    },
  },
  
  actions: {
    setTheme(newTheme) {
      this.theme = newTheme
      localStorage.setItem('theme', newTheme)
      
      // Dynamically set the Vuetify theme
      if (typeof window !== 'undefined') {
        // Update HTML attributes
        const effectiveTheme = this.effectiveTheme
        document.documentElement.setAttribute('data-theme', effectiveTheme)
        
        // Directly set Vuetify's theme
        const vuetifyApp = document.querySelector('.v-application')
        if (vuetifyApp) {
          vuetifyApp.classList.remove('v-theme--light', 'v-theme--dark')
          vuetifyApp.classList.add(`v-theme--${effectiveTheme}`)
        }
      }
    },
    
    // Handle system theme change
    handleSystemThemeChange() {
      if (this.theme === 'system') {
        this.applyEffectiveTheme()
      }
    },
    
    // Apply the effective theme without changing the theme preference
    applyEffectiveTheme() {
      const effectiveTheme = this.effectiveTheme
      
      if (typeof window !== 'undefined') {
        // Update HTML attributes
        document.documentElement.setAttribute('data-theme', effectiveTheme)
        
        // Directly set Vuetify's theme
        const vuetifyApp = document.querySelector('.v-application')
        if (vuetifyApp) {
          vuetifyApp.classList.remove('v-theme--light', 'v-theme--dark')
          vuetifyApp.classList.add(`v-theme--${effectiveTheme}`)
        }
      }
    },
    
    toggleTheme() {
      // Cycle through themes: light -> dark -> system -> light
      let newTheme
      switch (this.theme) {
        case 'light':
          newTheme = 'dark'
          break
        case 'dark':
          newTheme = 'system'
          break
        case 'system':
        default:
          newTheme = 'light'
          break
      }
      this.setTheme(newTheme)
    },
    
    initTheme() {
      // Apply theme on app initialization
      this.applyEffectiveTheme()
      
      // Add event listener for system theme changes
      if (typeof window !== 'undefined') {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
          this.handleSystemThemeChange()
        })
      }
    }
  }
})