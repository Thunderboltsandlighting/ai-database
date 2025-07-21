import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useConversationStore = defineStore('conversation', () => {
  // State
  const conversations = ref(new Map())
  const activeConversationId = ref('default')
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const currentConversation = computed(() => {
    return conversations.value.get(activeConversationId.value) || {
      id: activeConversationId.value,
      history: [],
      created: new Date().toISOString(),
      lastActivity: new Date().toISOString(),
      title: 'New Conversation'
    }
  })

  const conversationHistory = computed(() => {
    return currentConversation.value.history || []
  })

  const conversationCount = computed(() => {
    return conversations.value.size
  })

  // Actions
  function createConversation(id = null) {
    const conversationId = id || `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    const newConversation = {
      id: conversationId,
      history: [],
      created: new Date().toISOString(),
      lastActivity: new Date().toISOString(),
      title: 'New Conversation'
    }
    
    conversations.value.set(conversationId, newConversation)
    activeConversationId.value = conversationId
    
    // Persist to localStorage
    saveToStorage()
    
    return conversationId
  }

  function switchConversation(conversationId) {
    if (conversations.value.has(conversationId)) {
      activeConversationId.value = conversationId
      saveToStorage()
    } else {
      console.warn(`Conversation ${conversationId} not found`)
    }
  }

  function addMessage(message, conversationId = null) {
    const targetId = conversationId || activeConversationId.value
    
    if (!conversations.value.has(targetId)) {
      createConversation(targetId)
    }
    
    const conversation = conversations.value.get(targetId)
    conversation.history.push({
      ...message,
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString()
    })
    
    conversation.lastActivity = new Date().toISOString()
    
    // Update conversation title based on first user message
    if (conversation.history.length === 1 && message.role === 'user') {
      conversation.title = message.content.substring(0, 50) + (message.content.length > 50 ? '...' : '')
    }
    
    conversations.value.set(targetId, conversation)
    saveToStorage()
  }

  function updateLastMessage(updatedContent, conversationId = null) {
    const targetId = conversationId || activeConversationId.value
    const conversation = conversations.value.get(targetId)
    
    if (conversation && conversation.history.length > 0) {
      const lastMessage = conversation.history[conversation.history.length - 1]
      lastMessage.content = updatedContent
      lastMessage.timestamp = new Date().toISOString()
      
      conversation.lastActivity = new Date().toISOString()
      conversations.value.set(targetId, conversation)
      saveToStorage()
    }
  }

  function deleteConversation(conversationId) {
    if (conversations.value.has(conversationId)) {
      conversations.value.delete(conversationId)
      
      // If deleting active conversation, switch to another or create new
      if (activeConversationId.value === conversationId) {
        const remainingConversations = Array.from(conversations.value.keys())
        if (remainingConversations.length > 0) {
          activeConversationId.value = remainingConversations[0]
        } else {
          createConversation('default')
        }
      }
      
      saveToStorage()
    }
  }

  function clearCurrentConversation() {
    const conversation = conversations.value.get(activeConversationId.value)
    if (conversation) {
      conversation.history = []
      conversation.lastActivity = new Date().toISOString()
      conversations.value.set(activeConversationId.value, conversation)
      saveToStorage()
    }
  }

  function clearAllConversations() {
    conversations.value.clear()
    createConversation('default')
    saveToStorage()
  }

  function saveToStorage() {
    try {
      const conversationsObj = Object.fromEntries(conversations.value)
      const storeData = {
        conversations: conversationsObj,
        activeConversationId: activeConversationId.value,
        lastSaved: new Date().toISOString()
      }
      localStorage.setItem('hvlc_conversations', JSON.stringify(storeData))
    } catch (error) {
      console.error('Error saving conversations to localStorage:', error)
    }
  }

  function loadFromStorage() {
    try {
      const stored = localStorage.getItem('hvlc_conversations')
      if (stored) {
        const storeData = JSON.parse(stored)
        
        // Restore conversations
        conversations.value = new Map(Object.entries(storeData.conversations || {}))
        
        // Restore active conversation
        if (storeData.activeConversationId && conversations.value.has(storeData.activeConversationId)) {
          activeConversationId.value = storeData.activeConversationId
        }
        
        console.log(`Loaded ${conversations.value.size} conversations from storage`)
      }
    } catch (error) {
      console.error('Error loading conversations from localStorage:', error)
    }
    
    // Ensure we have at least one conversation
    if (conversations.value.size === 0) {
      createConversation('default')
    }
  }

  function exportConversations() {
    const conversationsObj = Object.fromEntries(conversations.value)
    return {
      conversations: conversationsObj,
      exportDate: new Date().toISOString(),
      version: '1.0'
    }
  }

  function importConversations(data) {
    try {
      if (data.conversations) {
        conversations.value = new Map(Object.entries(data.conversations))
        
        // Set active to first conversation if current active doesn't exist
        if (!conversations.value.has(activeConversationId.value)) {
          const firstConversation = Array.from(conversations.value.keys())[0]
          if (firstConversation) {
            activeConversationId.value = firstConversation
          }
        }
        
        saveToStorage()
        return true
      }
    } catch (error) {
      console.error('Error importing conversations:', error)
      return false
    }
    return false
  }

  // Initialize store
  function initialize() {
    loadFromStorage()
  }

  return {
    // State
    conversations,
    activeConversationId,
    isLoading,
    error,
    
    // Getters
    currentConversation,
    conversationHistory,
    conversationCount,
    
    // Actions
    createConversation,
    switchConversation,
    addMessage,
    updateLastMessage,
    deleteConversation,
    clearCurrentConversation,
    clearAllConversations,
    saveToStorage,
    loadFromStorage,
    exportConversations,
    importConversations,
    initialize
  }
}) 