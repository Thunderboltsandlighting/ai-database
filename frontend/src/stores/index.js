import { createPinia } from 'pinia'
import { useThemeStore } from './themeStore'
import { useConversationStore } from './conversationStore'
import { useAnalysisStore } from './analysisStore'
import { useFilesStore } from './filesStore'

export { 
  useThemeStore, 
  useConversationStore, 
  useAnalysisStore, 
  useFilesStore 
}

export default createPinia()