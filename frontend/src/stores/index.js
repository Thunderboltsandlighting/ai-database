import { createPinia } from 'pinia'
import { useThemeStore } from './themeStore'
import { useConversationStore } from './conversationStore'

export { useThemeStore, useConversationStore }

export default createPinia()