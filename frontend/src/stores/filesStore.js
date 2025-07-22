import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useFilesStore = defineStore('files', () => {
  // State
  const files = ref([])
  const uploadedFiles = ref([])
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const error = ref(null)

  // Actions
  const setFiles = (newFiles) => {
    files.value = newFiles
  }

  const addFile = (file) => {
    files.value.push(file)
  }

  const removeFile = (id) => {
    const index = files.value.findIndex(f => f.id === id)
    if (index > -1) {
      files.value.splice(index, 1)
    }
  }

  const setUploading = (state) => {
    uploading.value = state
  }

  const setUploadProgress = (progress) => {
    uploadProgress.value = progress
  }

  const setError = (errorMsg) => {
    error.value = errorMsg
  }

  const clearError = () => {
    error.value = null
  }

  const addUploadedFile = (file) => {
    uploadedFiles.value.push(file)
  }

  const clearUploadedFiles = () => {
    uploadedFiles.value = []
  }

  const updateFileStatus = (id, status) => {
    const index = files.value.findIndex(f => f.id === id)
    if (index > -1) {
      files.value[index].status = status
    }
  }

  return {
    // State
    files,
    uploadedFiles,
    uploading,
    uploadProgress,
    error,
    
    // Actions
    setFiles,
    addFile,
    removeFile,
    setUploading,
    setUploadProgress,
    setError,
    clearError,
    addUploadedFile,
    clearUploadedFiles,
    updateFileStatus
  }
}) 