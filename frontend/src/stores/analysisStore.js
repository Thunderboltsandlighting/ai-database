import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAnalysisStore = defineStore('analysis', () => {
  // State
  const analyses = ref([])
  const currentAnalysis = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Actions
  const setAnalyses = (newAnalyses) => {
    analyses.value = newAnalyses
  }

  const setCurrentAnalysis = (analysis) => {
    currentAnalysis.value = analysis
  }

  const setLoading = (state) => {
    loading.value = state
  }

  const setError = (errorMsg) => {
    error.value = errorMsg
  }

  const clearError = () => {
    error.value = null
  }

  const addAnalysis = (analysis) => {
    analyses.value.push(analysis)
  }

  const removeAnalysis = (id) => {
    const index = analyses.value.findIndex(a => a.id === id)
    if (index > -1) {
      analyses.value.splice(index, 1)
    }
  }

  const updateAnalysis = (id, updates) => {
    const index = analyses.value.findIndex(a => a.id === id)
    if (index > -1) {
      analyses.value[index] = { ...analyses.value[index], ...updates }
    }
  }

  return {
    // State
    analyses,
    currentAnalysis,
    loading,
    error,
    
    // Actions
    setAnalyses,
    setCurrentAnalysis,
    setLoading,
    setError,
    clearError,
    addAnalysis,
    removeAnalysis,
    updateAnalysis
  }
}) 