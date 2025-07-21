<template>
  <div class="ada-settings">
    <v-container>
      <v-row>
        <v-col cols="12">
          <h1 class="text-h3 mb-6">
            <v-icon large class="mr-3">mdi-robot</v-icon>
            Ada AI Assistant Settings
          </h1>
          <p class="text-subtitle-1 mb-6">Customize Ada's personality, memory, and behavior to match your preferences.</p>
        </v-col>
      </v-row>

      <v-row>
        <!-- Personality Settings -->
        <v-col cols="12" md="6">
          <v-card class="mb-4">
            <v-card-title>
              <v-icon class="mr-2">mdi-account-heart</v-icon>
              Personality
            </v-card-title>
            <v-card-text>
              <!-- Quick Presets -->
              <v-card-subtitle>Quick Presets</v-card-subtitle>
              <v-row class="mb-4">
                <v-col v-for="(preset, key) in presets" :key="key" cols="6">
                  <v-btn
                    :variant="selectedPreset === key ? 'elevated' : 'outlined'"
                    :color="selectedPreset === key ? 'primary' : 'default'"
                    block
                    @click="applyPreset(key)"
                    :loading="applyingPreset === key"
                  >
                    {{ preset.name }}
                  </v-btn>
                  <div class="text-caption mt-1">{{ preset.description }}</div>
                </v-col>
              </v-row>

              <!-- Manual Settings -->
              <v-card-subtitle>Custom Settings</v-card-subtitle>
              
              <v-select
                v-model="personalitySettings.communication_style"
                :items="communicationStyles"
                label="Communication Style"
                @update:model-value="updatePersonality"
                class="mb-3"
              ></v-select>

              <v-select
                v-model="personalitySettings.analysis_depth"
                :items="analysisDepths"
                label="Analysis Depth"
                @update:model-value="updatePersonality"
                class="mb-3"
              ></v-select>

              <v-switch
                v-model="personalitySettings.proactive_suggestions"
                label="Proactive Suggestions"
                @update:model-value="updatePersonality"
                color="primary"
              ></v-switch>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- User Context -->
        <v-col cols="12" md="6">
          <v-card class="mb-4">
            <v-card-title>
              <v-icon class="mr-2">mdi-account-circle</v-icon>
              Your Information
            </v-card-title>
            <v-card-text>
              <v-text-field
                v-model="userContext.user_name"
                label="Your Name"
                @blur="updateUserContext"
                class="mb-3"
              ></v-text-field>

              <v-select
                v-model="userContext.role"
                :items="userRoles"
                label="Your Role"
                @update:model-value="updateUserContext"
                class="mb-3"
              ></v-select>

              <v-text-field
                v-model="userContext.organization"
                label="Organization"
                @blur="updateUserContext"
                class="mb-3"
              ></v-text-field>

              <v-select
                v-model="userContext.timezone"
                :items="timezones"
                label="Timezone"
                @update:model-value="updateUserContext"
              ></v-select>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row>
        <!-- Custom Instructions -->
        <v-col cols="12" md="8">
          <v-card class="mb-4">
            <v-card-title>
              <v-icon class="mr-2">mdi-script-text</v-icon>
              Custom Instructions
            </v-card-title>
            <v-card-text>
              <!-- Add new instruction -->
              <v-row class="mb-4">
                <v-col cols="3">
                  <v-select
                    v-model="newInstruction.category"
                    :items="instructionCategories"
                    label="Category"
                  ></v-select>
                </v-col>
                <v-col cols="7">
                  <v-text-field
                    v-model="newInstruction.instruction"
                    label="Instruction"
                    placeholder="e.g., Always explain medical billing terms"
                  ></v-text-field>
                </v-col>
                <v-col cols="2">
                  <v-btn
                    color="primary"
                    @click="addInstruction"
                    :disabled="!newInstruction.instruction"
                    block
                  >
                    Add
                  </v-btn>
                </v-col>
              </v-row>

              <!-- Existing instructions -->
              <v-list v-if="instructions.length">
                <v-list-item
                  v-for="instruction in instructions"
                  :key="instruction.instruction_id"
                  class="mb-2"
                >
                  <template v-slot:prepend>
                    <v-chip
                      size="small"
                      :color="getCategoryColor(instruction.category)"
                      variant="outlined"
                    >
                      {{ instruction.category }}
                    </v-chip>
                  </template>

                  <v-list-item-title>{{ instruction.instruction }}</v-list-item-title>

                  <template v-slot:append>
                    <v-chip size="small" class="mr-2">
                      Priority: {{ instruction.priority }}
                    </v-chip>
                    <v-btn
                      icon="mdi-delete"
                      size="small"
                      color="error"
                      variant="text"
                      @click="deleteInstruction(instruction.instruction_id)"
                    ></v-btn>
                  </template>
                </v-list-item>
              </v-list>
              <div v-else class="text-center text-grey-500 py-4">
                No custom instructions yet. Add one above!
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Recent Memories -->
        <v-col cols="12" md="4">
          <v-card class="mb-4">
            <v-card-title>
              <v-icon class="mr-2">mdi-brain</v-icon>
              Recent Memories
            </v-card-title>
            <v-card-text>
              <v-list v-if="memories.length">
                <v-list-item
                  v-for="memory in memories.slice(0, 5)"
                  :key="memory.memory_id"
                  class="mb-2"
                >
                  <template v-slot:prepend>
                    <v-chip
                      size="small"
                      :color="getMemoryTypeColor(memory.memory_type)"
                      variant="outlined"
                    >
                      {{ memory.memory_type }}
                    </v-chip>
                  </template>

                  <v-list-item-title class="text-caption">
                    {{ memory.content.substring(0, 80) }}...
                  </v-list-item-title>

                  <v-list-item-subtitle>
                    {{ formatDate(memory.created_at) }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
              <div v-else class="text-center text-grey-500 py-4">
                No memories stored yet.
              </div>

              <v-btn
                variant="outlined"
                block
                @click="loadMemories"
                class="mt-3"
              >
                Refresh Memories
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row>
        <!-- Actions -->
        <v-col cols="12">
          <v-card>
            <v-card-title>
              <v-icon class="mr-2">mdi-cog</v-icon>
              Actions
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="auto">
                  <v-btn
                    color="primary"
                    @click="testAda"
                    :loading="testing"
                  >
                    Test Ada's Current Settings
                  </v-btn>
                </v-col>
                <v-col cols="auto">
                  <v-btn
                    color="orange"
                    variant="outlined"
                    @click="resetToDefaults"
                    :loading="resetting"
                  >
                    Reset to Defaults
                  </v-btn>
                </v-col>
                <v-col cols="auto">
                  <v-btn
                    color="info"
                    variant="outlined"
                    @click="viewSystemPrompt"
                  >
                    View System Prompt
                  </v-btn>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <!-- System Prompt Dialog -->
    <v-dialog v-model="systemPromptDialog" max-width="800">
      <v-card>
        <v-card-title>Ada's Current System Prompt</v-card-title>
        <v-card-text>
          <v-textarea
            :value="systemPrompt"
            readonly
            rows="20"
            class="text-caption"
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="systemPromptDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn
          text
          @click="snackbar.show = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdaSettingsView',
  data() {
    return {
      // Personality settings
      personalitySettings: {
        communication_style: 'friendly',
        analysis_depth: 'standard',
        proactive_suggestions: true
      },
      presets: {},
      selectedPreset: null,
      applyingPreset: null,
      
      // User context
      userContext: {
        user_name: '',
        role: '',
        organization: '',
        timezone: 'UTC'
      },
      
      // Instructions
      instructions: [],
      newInstruction: {
        category: 'general',
        instruction: ''
      },
      
      // Memories
      memories: [],
      
      // UI state
      loading: false,
      testing: false,
      resetting: false,
      systemPromptDialog: false,
      systemPrompt: '',
      
      // Snackbar
      snackbar: {
        show: false,
        text: '',
        color: 'success',
        timeout: 3000
      },
      
      // Options
      communicationStyles: [
        { title: 'Professional', value: 'professional' },
        { title: 'Friendly', value: 'friendly' },
        { title: 'Casual', value: 'casual' },
        { title: 'Technical', value: 'technical' },
        { title: 'Concise', value: 'concise' }
      ],
      analysisDepths: [
        { title: 'Basic', value: 'basic' },
        { title: 'Standard', value: 'standard' },
        { title: 'Detailed', value: 'detailed' },
        { title: 'Expert', value: 'expert' }
      ],
      userRoles: [
        { title: 'Administrator', value: 'administrator' },
        { title: 'Analyst', value: 'analyst' },
        { title: 'Provider', value: 'provider' },
        { title: 'Manager', value: 'manager' }
      ],
      instructionCategories: [
        { title: 'General', value: 'general' },
        { title: 'Analysis', value: 'analysis' },
        { title: 'Communication', value: 'communication' },
        { title: 'Reporting', value: 'reporting' }
      ],
      timezones: [
        { title: 'UTC', value: 'UTC' },
        { title: 'US/Eastern', value: 'US/Eastern' },
        { title: 'US/Central', value: 'US/Central' },
        { title: 'US/Mountain', value: 'US/Mountain' },
        { title: 'US/Pacific', value: 'US/Pacific' }
      ]
    }
  },
  
  async mounted() {
    await this.loadSettings()
  },
  
  methods: {
    async loadSettings() {
      this.loading = true
      try {
        // Load presets
        const presetsResponse = await axios.get('/api/ada/presets')
        this.presets = presetsResponse.data.presets
        
        // Load current personality
        const personalityResponse = await axios.get('/api/ada/personality')
        const personality = personalityResponse.data.personality
        
        // Extract current settings
        if (personality.communication?.tone) {
          const toneValue = personality.communication.tone.value
          this.personalitySettings.communication_style = this.mapToneToStyle(toneValue)
        }
        if (personality.analysis?.depth) {
          this.personalitySettings.analysis_depth = personality.analysis.depth.value
        }
        if (personality.analysis?.proactivity) {
          this.personalitySettings.proactive_suggestions = personality.analysis.proactivity.value === 'high'
        }
        
        // Load user context
        const contextResponse = await axios.get('/api/ada/user-context')
        if (contextResponse.data.context) {
          this.userContext = { ...this.userContext, ...contextResponse.data.context }
        }
        
        // Load instructions
        await this.loadInstructions()
        
        // Load memories
        await this.loadMemories()
        
      } catch (error) {
        this.showSnackbar('Failed to load Ada settings', 'error')
        console.error('Error loading settings:', error)
      }
      this.loading = false
    },
    
    async loadInstructions() {
      try {
        const response = await axios.get('/api/ada/instructions')
        this.instructions = response.data.instructions
      } catch (error) {
        console.error('Error loading instructions:', error)
      }
    },
    
    async loadMemories() {
      try {
        const response = await axios.get('/api/ada/memories?limit=10')
        this.memories = response.data.memories
      } catch (error) {
        console.error('Error loading memories:', error)
      }
    },
    
    async updatePersonality() {
      try {
        await axios.post('/api/ada/personality', this.personalitySettings)
        this.showSnackbar('Personality updated successfully')
      } catch (error) {
        this.showSnackbar('Failed to update personality', 'error')
        console.error('Error updating personality:', error)
      }
    },
    
    async updateUserContext() {
      try {
        await axios.post('/api/ada/user-context', this.userContext)
        this.showSnackbar('User context updated')
      } catch (error) {
        this.showSnackbar('Failed to update user context', 'error')
        console.error('Error updating context:', error)
      }
    },
    
    async applyPreset(presetName) {
      this.applyingPreset = presetName
      try {
        const response = await axios.post(`/api/ada/presets/${presetName}`)
        this.selectedPreset = presetName
        this.showSnackbar(`Applied ${this.presets[presetName].name} preset`)
        
        // Reload settings to reflect changes
        await this.loadSettings()
      } catch (error) {
        this.showSnackbar('Failed to apply preset', 'error')
        console.error('Error applying preset:', error)
      }
      this.applyingPreset = null
    },
    
    async addInstruction() {
      try {
        await axios.post('/api/ada/instructions', this.newInstruction)
        this.newInstruction.instruction = ''
        await this.loadInstructions()
        this.showSnackbar('Instruction added successfully')
      } catch (error) {
        this.showSnackbar('Failed to add instruction', 'error')
        console.error('Error adding instruction:', error)
      }
    },
    
    async deleteInstruction(instructionId) {
      try {
        await axios.delete(`/api/ada/instructions/${instructionId}`)
        await this.loadInstructions()
        this.showSnackbar('Instruction removed')
      } catch (error) {
        this.showSnackbar('Failed to remove instruction', 'error')
        console.error('Error removing instruction:', error)
      }
    },
    
    async testAda() {
      this.testing = true
      try {
        const response = await axios.post('/api/ai/chat', {
          message: 'Hello Ada! Can you introduce yourself with your current personality settings?',
          history: []
        })
        
        this.showSnackbar('Test completed - check the Chat page for Ada\'s response!')
        this.$router.push('/chat')
      } catch (error) {
        this.showSnackbar('Failed to test Ada', 'error')
        console.error('Error testing Ada:', error)
      }
      this.testing = false
    },
    
    async resetToDefaults() {
      this.resetting = true
      try {
        await axios.post('/api/ada/reset')
        this.showSnackbar('Ada reset to default settings')
        await this.loadSettings()
      } catch (error) {
        this.showSnackbar('Failed to reset Ada', 'error')
        console.error('Error resetting Ada:', error)
      }
      this.resetting = false
    },
    
    async viewSystemPrompt() {
      try {
        const response = await axios.get('/api/ada/system-prompt')
        this.systemPrompt = response.data.system_prompt
        this.systemPromptDialog = true
      } catch (error) {
        this.showSnackbar('Failed to load system prompt', 'error')
        console.error('Error loading system prompt:', error)
      }
    },
    
    // Helper methods
    mapToneToStyle(tone) {
      const mapping = {
        'formal_professional': 'professional',
        'friendly_professional': 'friendly',
        'casual_friendly': 'casual',
        'technical_detailed': 'technical',
        'brief_direct': 'concise'
      }
      return mapping[tone] || 'friendly'
    },
    
    getCategoryColor(category) {
      const colors = {
        general: 'blue',
        analysis: 'green',
        communication: 'purple',
        reporting: 'orange'
      }
      return colors[category] || 'grey'
    },
    
    getMemoryTypeColor(type) {
      const colors = {
        conversation: 'blue',
        insight: 'green',
        preference: 'purple',
        fact: 'orange'
      }
      return colors[type] || 'grey'
    },
    
    formatDate(dateString) {
      return new Date(dateString).toLocaleDateString()
    },
    
    showSnackbar(text, color = 'success') {
      this.snackbar.text = text
      this.snackbar.color = color
      this.snackbar.show = true
    }
  }
}
</script>

<style scoped>
.ada-settings {
  max-width: 1400px;
  margin: 0 auto;
}
</style> 