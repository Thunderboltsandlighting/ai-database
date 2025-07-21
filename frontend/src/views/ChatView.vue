<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-6">
          <v-icon left color="primary">mdi-robot</v-icon>
          Ada Assistant
        </h1>
      </v-col>
    </v-row>

    <!-- Conversation Management -->
    <v-row v-if="conversationStore.conversationCount > 1" class="mb-4">
      <v-col cols="12">
        <v-card>
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div class="d-flex align-center">
                <v-icon left>mdi-chat</v-icon>
                <span class="text-subtitle-1">Conversations ({{ conversationStore.conversationCount }})</span>
              </div>
              <div>
                <v-btn
                  size="small"
                  color="primary"
                  @click="startNewConversation"
                  class="mr-2"
                >
                  <v-icon left>mdi-plus</v-icon>
                  New Chat
                </v-btn>
                <v-btn
                  size="small"
                  color="warning"
                  @click="clearCurrentConversation"
                  :disabled="conversationStore.conversationHistory.length === 0"
                >
                  <v-icon left>mdi-broom</v-icon>
                  Clear
                </v-btn>
              </div>
            </div>
            <v-divider class="my-3"></v-divider>
            <div class="conversation-tabs">
              <v-chip
                v-for="[id, conversation] in conversationStore.conversations"
                :key="id"
                :color="id === conversationStore.activeConversationId ? 'primary' : 'default'"
                :variant="id === conversationStore.activeConversationId ? 'flat' : 'outlined'"
                @click="switchConversation(id)"
                closable
                @click:close="deleteConversation(id)"
                class="ma-1"
                size="small"
              >
                {{ conversation.title }}
              </v-chip>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Chat Interface -->
    <v-row>
      <v-col cols="12">
        <v-card height="600">
          <!-- Chat Messages -->
          <v-card-text class="chat-container" ref="chatContainer">
            <div v-if="conversationStore.conversationHistory.length === 0" class="text-center py-8">
              <v-icon size="64" color="grey-lighten-1">mdi-chat-outline</v-icon>
              <p class="text-h6 text-grey-lighten-1 mt-4">Start a conversation with Ada</p>
              <p class="text-body-2 text-grey">Ask about provider performance, revenue analysis, or any medical billing question</p>
            </div>

            <div
              v-for="message in conversationStore.conversationHistory"
              :key="message.id"
              class="message mb-4"
              :class="{'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant'}"
            >
              <div class="message-header d-flex align-center mb-2">
                <v-avatar size="32" :color="message.role === 'user' ? 'blue' : 'green'" class="mr-3">
                  <v-icon color="white">
                    {{ message.role === 'user' ? 'mdi-account' : 'mdi-robot' }}
                  </v-icon>
                </v-avatar>
                <div>
                  <div class="font-weight-medium">
                    {{ message.role === 'user' ? 'You' : 'Ada' }}
                  </div>
                  <div class="text-caption text-grey">
                    {{ formatTimestamp(message.timestamp) }}
                  </div>
                </div>
              </div>
              
              <div class="message-content">
                <div v-if="message.role === 'user'" class="user-content">
                  {{ message.content }}
                </div>
                <div v-else class="assistant-content">
                  <div v-if="message.content" v-html="formatResponse(message.content)"></div>
                  <div v-else-if="message === typingMessage" class="typing-indicator">
                    <v-progress-circular indeterminate size="16" width="2"></v-progress-circular>
                    <span class="ml-2">Ada is thinking...</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Typing Indicator -->
            <div v-if="isLoading && !typingMessage" class="message assistant-message mb-4">
              <div class="message-header d-flex align-center mb-2">
                <v-avatar size="32" color="green" class="mr-3">
                  <v-icon color="white">mdi-robot</v-icon>
                </v-avatar>
                <div>
                  <div class="font-weight-medium">Ada</div>
                  <div class="text-caption text-grey">thinking...</div>
                </div>
              </div>
              <div class="message-content">
                <div class="typing-indicator">
                  <v-progress-circular indeterminate size="16" width="2"></v-progress-circular>
                  <span class="ml-2">Ada is analyzing your data...</span>
                </div>
              </div>
            </div>
          </v-card-text>

          <!-- Input Area -->
          <v-divider></v-divider>
          <v-card-actions class="pa-4">
            <v-row no-gutters align="center">
              <v-col>
                <v-textarea
                  v-model="newMessage"
                  placeholder="Ask Ada about your medical billing data..."
                  rows="2"
                  auto-grow
                  variant="outlined"
                  hide-details
                  @keydown.enter.prevent="sendMessage"
                  @keydown.shift.enter="newMessage += '\n'"
                  :disabled="isLoading"
                  class="mr-3"
                ></v-textarea>
              </v-col>
              <v-col cols="auto">
                <v-btn
                  color="primary"
                  size="large"
                  :disabled="!newMessage.trim() || isLoading"
                  @click="sendMessage"
                  icon
                >
                  <v-icon>mdi-send</v-icon>
                </v-btn>
              </v-col>
            </v-row>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-lightning-bolt</v-icon>
            Quick Questions
          </v-card-title>
          <v-card-text>
            <v-chip-group>
              <v-chip
                v-for="question in quickQuestions"
                :key="question"
                @click="askQuickQuestion(question)"
                variant="outlined"
                size="small"
                class="ma-1"
              >
                {{ question }}
              </v-chip>
            </v-chip-group>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useConversationStore } from '../stores/conversationStore'
import { aiApi } from '../services/api'

export default {
  name: 'ChatView',
  setup() {
    const conversationStore = useConversationStore()
    const newMessage = ref('')
    const isLoading = ref(false)
    const typingMessage = ref(null)
    const chatContainer = ref(null)

    const quickQuestions = [
      "How is Dustin's 2025 performance?",
      "Compare Dustin vs Tammy revenue",
      "What are my monthly overhead expenses?",
      "Is Dustin covering our overhead costs?",
      "Show me provider performance trends",
      "What's my practice's financial summary?"
    ]

    const sendMessage = async () => {
      if (!newMessage.value.trim() || isLoading.value) return

      const userMessage = {
        role: 'user',
        content: newMessage.value.trim()
      }

      // Add user message to conversation
      conversationStore.addMessage(userMessage)
      
      // Clear input
      const messageToSend = newMessage.value.trim()
      newMessage.value = ''
      
      // Scroll to bottom
      nextTick(() => scrollToBottom())

      // Start loading
      isLoading.value = true

      try {
        // Send to API with conversation history
        const response = await aiApi.sendMessage({
          message: messageToSend,
          history: conversationStore.conversationHistory
        })

        // Add assistant response
        const assistantMessage = {
          role: 'assistant',
          content: response.data.response || 'I apologize, but I encountered an issue processing your request.'
        }

        conversationStore.addMessage(assistantMessage)
        
        // Scroll to bottom
        nextTick(() => scrollToBottom())

      } catch (error) {
        console.error('Error sending message:', error)
        
        const errorMessage = {
          role: 'assistant',
          content: 'I apologize, but I encountered an error. Please try again or check if the API server is running.'
        }
        
        conversationStore.addMessage(errorMessage)
      } finally {
        isLoading.value = false
        typingMessage.value = null
      }
    }

    const askQuickQuestion = (question) => {
      newMessage.value = question
      sendMessage()
    }

    const startNewConversation = () => {
      conversationStore.createConversation()
    }

    const switchConversation = (conversationId) => {
      conversationStore.switchConversation(conversationId)
      nextTick(() => scrollToBottom())
    }

    const deleteConversation = (conversationId) => {
      if (conversationStore.conversationCount > 1) {
        conversationStore.deleteConversation(conversationId)
      }
    }

    const clearCurrentConversation = () => {
      conversationStore.clearCurrentConversation()
    }

    const scrollToBottom = () => {
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
      }
    }

    const formatTimestamp = (timestamp) => {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
      })
    }

    const formatResponse = (content) => {
      if (!content) return ''
      
      // Convert markdown-style formatting to HTML
      let formatted = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>')
      
      return formatted
    }

    // Watch for conversation changes to scroll to bottom
    watch(() => conversationStore.conversationHistory.length, () => {
      nextTick(() => scrollToBottom())
    })

    onMounted(() => {
      // Initialize conversation store
      conversationStore.initialize()
      
      // Scroll to bottom if there are existing messages
      nextTick(() => scrollToBottom())
    })

    return {
      conversationStore,
      newMessage,
      isLoading,
      typingMessage,
      chatContainer,
      quickQuestions,
      sendMessage,
      askQuickQuestion,
      startNewConversation,
      switchConversation,
      deleteConversation,
      clearCurrentConversation,
      formatTimestamp,
      formatResponse
    }
  }
}
</script>

<style scoped>
.chat-container {
  height: 450px;
  overflow-y: auto;
  padding: 16px;
}

.message {
  max-width: 100%;
}

.user-message {
  margin-left: 20%;
}

.assistant-message {
  margin-right: 20%;
}

.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  margin-left: 44px;
}

.user-content {
  background-color: rgb(var(--v-theme-primary));
  color: white;
}

.assistant-content {
  background-color: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-on-surface-variant));
}

.typing-indicator {
  display: flex;
  align-items: center;
  font-style: italic;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.conversation-tabs {
  max-height: 120px;
  overflow-y: auto;
}

:deep(code) {
  background-color: rgba(var(--v-theme-on-surface), 0.1);
  padding: 2px 4px;
  border-radius: 4px;
  font-family: 'Roboto Mono', monospace;
}
</style>