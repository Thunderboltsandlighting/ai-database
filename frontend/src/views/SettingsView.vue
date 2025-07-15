<template>
  <div class="settings-view">
    <h1>Settings</h1>
    
    <v-row>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>Navigation</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item
                v-for="(section, index) in sections"
                :key="index"
                :title="section"
                @click="scrollToSection(section)"
                rounded="lg"
              ></v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="8">
        <v-card id="application" class="mb-4">
          <v-card-title>Application Settings</v-card-title>
          <v-card-text>
            <v-form ref="appSettingsForm">
              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="appSettings.theme"
                    :items="themeOptions"
                    label="Theme"
                  ></v-select>
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="appSettings.dateFormat"
                    :items="dateFormatOptions"
                    label="Date Format"
                  ></v-select>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="appSettings.itemsPerPage"
                    :items="itemsPerPageOptions"
                    label="Items Per Page"
                  ></v-select>
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="appSettings.currency"
                    :items="currencyOptions"
                    label="Currency"
                  ></v-select>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12">
                  <v-checkbox
                    v-model="appSettings.autoRefresh"
                    label="Enable auto-refresh"
                  ></v-checkbox>
                </v-col>
              </v-row>
            </v-form>
            
            <v-divider class="my-4"></v-divider>
            
            <div class="d-flex justify-end">
              <v-btn
                color="primary"
                @click="saveAppSettings"
                :loading="saving"
              >
                Save Application Settings
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
        
        <v-card id="database" class="mb-4">
          <v-card-title>Database Settings</v-card-title>
          <v-card-text>
            <v-form ref="dbSettingsForm">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="dbSettings.path"
                    label="Database Path"
                    placeholder="medical_billing.db"
                    hint="Path to SQLite database file"
                    persistent-hint
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="dbSettings.backupFrequency"
                    :items="backupFrequencyOptions"
                    label="Backup Frequency"
                  ></v-select>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12">
                  <v-text-field
                    v-model="dbSettings.backupPath"
                    label="Backup Path"
                    placeholder="backups/"
                    hint="Directory to store database backups"
                    persistent-hint
                  ></v-text-field>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12">
                  <v-checkbox
                    v-model="dbSettings.autoBackup"
                    label="Enable automatic backups"
                  ></v-checkbox>
                </v-col>
              </v-row>
            </v-form>
            
            <v-divider class="my-4"></v-divider>
            
            <div class="d-flex justify-end">
              <v-btn
                color="warning"
                class="mr-2"
                @click="backupNow"
                :loading="backingUp"
              >
                Backup Now
              </v-btn>
              <v-btn
                color="primary"
                @click="saveDbSettings"
                :loading="saving"
              >
                Save Database Settings
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
        
        <v-card id="ai" class="mb-4">
          <v-card-title>AI Settings</v-card-title>
          <v-card-text>
            <v-form ref="aiSettingsForm">
              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="aiSettings.model"
                    :items="aiModelOptions"
                    label="AI Model"
                  ></v-select>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="aiSettings.timeout"
                    label="Timeout (seconds)"
                    type="number"
                    min="10"
                    max="300"
                  ></v-text-field>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="aiSettings.ollamaServer"
                    :items="ollamaServerOptions"
                    label="Ollama Server"
                  ></v-select>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="aiSettings.ollamaEndpoint"
                    label="Ollama Endpoint"
                    placeholder="http://localhost:11434"
                  ></v-text-field>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12">
                  <v-checkbox
                    v-model="aiSettings.enableFallback"
                    label="Enable model fallback"
                  ></v-checkbox>
                </v-col>
              </v-row>
            </v-form>
            
            <v-divider class="my-4"></v-divider>
            
            <div class="d-flex justify-end">
              <v-btn
                color="info"
                class="mr-2"
                @click="testAiConnection"
                :loading="testingAi"
              >
                Test Connection
              </v-btn>
              <v-btn
                color="primary"
                @click="saveAiSettings"
                :loading="saving"
              >
                Save AI Settings
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
        
        <v-card id="import" class="mb-4">
          <v-card-title>Import/Export Settings</v-card-title>
          <v-card-text>
            <v-form ref="importSettingsForm">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="importSettings.csvFolder"
                    label="CSV Folder"
                    placeholder="csv_folder/"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="importSettings.uploadFolder"
                    label="Upload Folder"
                    placeholder="uploads/"
                  ></v-text-field>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="importSettings.defaultDelimiter"
                    :items="delimiterOptions"
                    label="Default CSV Delimiter"
                  ></v-select>
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="importSettings.dateFormat"
                    :items="dateFormatOptions"
                    label="CSV Date Format"
                  ></v-select>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12">
                  <v-checkbox
                    v-model="importSettings.detectFormats"
                    label="Enable automatic format detection"
                  ></v-checkbox>
                </v-col>
              </v-row>
            </v-form>
            
            <v-divider class="my-4"></v-divider>
            
            <div class="d-flex justify-end">
              <v-btn
                color="primary"
                @click="saveImportSettings"
                :loading="saving"
              >
                Save Import/Export Settings
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
        
        <v-card id="system" class="mb-4">
          <v-card-title>System Settings</v-card-title>
          <v-card-text>
            <v-form ref="systemSettingsForm">
              <v-row>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="systemSettings.logLevel"
                    :items="logLevelOptions"
                    label="Log Level"
                  ></v-select>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="systemSettings.logFile"
                    label="Log File"
                    placeholder="logs/hvlc_db.log"
                  ></v-text-field>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12">
                  <v-checkbox
                    v-model="systemSettings.debugMode"
                    label="Enable debug mode"
                  ></v-checkbox>
                </v-col>
              </v-row>
              
              <v-row>
                <v-col cols="12">
                  <v-text-field
                    v-model="systemSettings.tempFolder"
                    label="Temporary Files Folder"
                    placeholder="temp/"
                  ></v-text-field>
                </v-col>
              </v-row>
            </v-form>
            
            <v-divider class="my-4"></v-divider>
            
            <div class="d-flex justify-end">
              <v-btn
                color="error"
                class="mr-2"
                @click="showResetDialog = true"
              >
                Reset All Settings
              </v-btn>
              <v-btn
                color="primary"
                @click="saveSystemSettings"
                :loading="saving"
              >
                Save System Settings
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    
    <!-- Reset Confirmation Dialog -->
    <v-dialog v-model="showResetDialog" max-width="500">
      <v-card>
        <v-card-title>Reset All Settings</v-card-title>
        <v-card-text>
          Are you sure you want to reset all settings to default values? This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showResetDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="resetAllSettings">Reset All</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :timeout="3000"
      :color="snackbar.color"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn
          color="white"
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
import { useThemeStore } from '../stores/themeStore';

export default {
  name: 'SettingsView',
  setup() {
    const themeStore = useThemeStore();
    return { themeStore };
  },
  data() {
    return {
      saving: false,
      backingUp: false,
      testingAi: false,
      showResetDialog: false,
      
      sections: [
        'Application',
        'Database',
        'AI',
        'Import/Export',
        'System'
      ],
      
      appSettings: {
        theme: 'light',
        dateFormat: 'MM/DD/YYYY',
        itemsPerPage: 25,
        currency: 'USD',
        autoRefresh: true
      },
      
      dbSettings: {
        path: 'medical_billing.db',
        backupFrequency: 'Daily',
        backupPath: 'backups/',
        autoBackup: true
      },
      
      aiSettings: {
        model: 'llama3.1:8b',
        timeout: 60,
        ollamaServer: 'Laptop',
        ollamaEndpoint: 'http://localhost:11434',
        enableFallback: true
      },
      
      importSettings: {
        csvFolder: 'csv_folder/',
        uploadFolder: 'uploads/',
        defaultDelimiter: ',',
        dateFormat: 'YYYY-MM-DD',
        detectFormats: true
      },
      
      systemSettings: {
        logLevel: 'INFO',
        logFile: 'logs/hvlc_db.log',
        debugMode: false,
        tempFolder: 'temp/'
      },
      
      themeOptions: [
        'light',
        'dark',
        'system'
      ],
      
      dateFormatOptions: [
        'MM/DD/YYYY',
        'DD/MM/YYYY',
        'YYYY-MM-DD',
        'YYYY/MM/DD'
      ],
      
      itemsPerPageOptions: [
        10,
        25,
        50,
        100
      ],
      
      currencyOptions: [
        'USD',
        'EUR',
        'GBP',
        'CAD',
        'AUD'
      ],
      
      backupFrequencyOptions: [
        'Hourly',
        'Daily',
        'Weekly',
        'Monthly',
        'Never'
      ],
      
      aiModelOptions: [
        'llama3.1:8b',
        'llama3.3:70b',
        'mistral:v0.3',
        'mistral:latest',
        'granite-code:8b',
        'deepseek-r1:8b'
      ],
      
      ollamaServerOptions: [
        'Laptop',
        'Homelab',
        'Custom'
      ],
      
      delimiterOptions: [
        { text: 'Comma (,)', value: ',' },
        { text: 'Semicolon (;)', value: ';' },
        { text: 'Tab (\\t)', value: '\t' },
        { text: 'Pipe (|)', value: '|' }
      ],
      
      logLevelOptions: [
        'DEBUG',
        'INFO',
        'WARNING',
        'ERROR',
        'CRITICAL'
      ],
      
      snackbar: {
        show: false,
        text: '',
        color: 'success'
      }
    };
  },
  methods: {
    scrollToSection(section) {
      const element = document.getElementById(section.toLowerCase());
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    },
    
    async saveAppSettings() {
      this.saving = true;
      
      try {
        // Update theme in theme store
        this.themeStore.setTheme(this.appSettings.theme);
        
        // In real implementation, send to API
        // await axios.post('/api/settings/application', this.appSettings);
        
        // For demo, simulate API call
        setTimeout(() => {
          this.showSnackbar('Application settings saved successfully', 'success');
          this.saving = false;
        }, 800);
      } catch (error) {
        this.showSnackbar(`Error saving application settings: ${error.message}`, 'error');
        this.saving = false;
      }
    },
    
    async saveDbSettings() {
      this.saving = true;
      
      try {
        // In real implementation, send to API
        // await axios.post('/api/settings/database', this.dbSettings);
        
        // For demo, simulate API call
        setTimeout(() => {
          this.showSnackbar('Database settings saved successfully', 'success');
          this.saving = false;
        }, 800);
      } catch (error) {
        this.showSnackbar(`Error saving database settings: ${error.message}`, 'error');
        this.saving = false;
      }
    },
    
    async saveAiSettings() {
      this.saving = true;
      
      try {
        // In real implementation, send to API
        // await axios.post('/api/settings/ai', this.aiSettings);
        
        // For demo, simulate API call
        setTimeout(() => {
          this.showSnackbar('AI settings saved successfully', 'success');
          this.saving = false;
        }, 800);
      } catch (error) {
        this.showSnackbar(`Error saving AI settings: ${error.message}`, 'error');
        this.saving = false;
      }
    },
    
    async saveImportSettings() {
      this.saving = true;
      
      try {
        // In real implementation, send to API
        // await axios.post('/api/settings/import', this.importSettings);
        
        // For demo, simulate API call
        setTimeout(() => {
          this.showSnackbar('Import/Export settings saved successfully', 'success');
          this.saving = false;
        }, 800);
      } catch (error) {
        this.showSnackbar(`Error saving Import/Export settings: ${error.message}`, 'error');
        this.saving = false;
      }
    },
    
    async saveSystemSettings() {
      this.saving = true;
      
      try {
        // In real implementation, send to API
        // await axios.post('/api/settings/system', this.systemSettings);
        
        // For demo, simulate API call
        setTimeout(() => {
          this.showSnackbar('System settings saved successfully', 'success');
          this.saving = false;
        }, 800);
      } catch (error) {
        this.showSnackbar(`Error saving system settings: ${error.message}`, 'error');
        this.saving = false;
      }
    },
    
    async backupNow() {
      this.backingUp = true;
      
      try {
        // In real implementation, send to API
        // await axios.post('/api/database/backup');
        
        // For demo, simulate API call
        setTimeout(() => {
          this.showSnackbar('Database backed up successfully', 'success');
          this.backingUp = false;
        }, 1500);
      } catch (error) {
        this.showSnackbar(`Error backing up database: ${error.message}`, 'error');
        this.backingUp = false;
      }
    },
    
    async testAiConnection() {
      this.testingAi = true;
      
      try {
        // In real implementation, send to API
        // await axios.post('/api/ai/test-connection', this.aiSettings);
        
        // For demo, simulate API call
        setTimeout(() => {
          this.showSnackbar('AI connection successful. Model is available.', 'success');
          this.testingAi = false;
        }, 1200);
      } catch (error) {
        this.showSnackbar(`Error connecting to AI: ${error.message}`, 'error');
        this.testingAi = false;
      }
    },
    
    resetAllSettings() {
      // Reset all settings to default values
      this.appSettings = {
        theme: 'light',
        dateFormat: 'MM/DD/YYYY',
        itemsPerPage: 25,
        currency: 'USD',
        autoRefresh: true
      };
      
      this.dbSettings = {
        path: 'medical_billing.db',
        backupFrequency: 'Daily',
        backupPath: 'backups/',
        autoBackup: true
      };
      
      this.aiSettings = {
        model: 'llama3.1:8b',
        timeout: 60,
        ollamaServer: 'Laptop',
        ollamaEndpoint: 'http://localhost:11434',
        enableFallback: true
      };
      
      this.importSettings = {
        csvFolder: 'csv_folder/',
        uploadFolder: 'uploads/',
        defaultDelimiter: ',',
        dateFormat: 'YYYY-MM-DD',
        detectFormats: true
      };
      
      this.systemSettings = {
        logLevel: 'INFO',
        logFile: 'logs/hvlc_db.log',
        debugMode: false,
        tempFolder: 'temp/'
      };
      
      this.showResetDialog = false;
      this.showSnackbar('All settings reset to default values', 'info');
    },
    
    showSnackbar(text, color) {
      this.snackbar.text = text;
      this.snackbar.color = color;
      this.snackbar.show = true;
    },
    
    async loadSettings() {
      try {
        // In real implementation, fetch from API
        // const response = await axios.get('/api/settings');
        // this.appSettings = response.data.application;
        // this.dbSettings = response.data.database;
        // this.aiSettings = response.data.ai;
        // this.importSettings = response.data.import;
        // this.systemSettings = response.data.system;
        
        // For demo, use default values
      } catch (error) {
        this.showSnackbar(`Error loading settings: ${error.message}`, 'error');
      }
    }
  },
  mounted() {
    this.loadSettings();
    // Initialize theme from store
    this.appSettings.theme = this.themeStore.currentTheme;
  }
};
</script>

<style scoped>
.settings-view {
  padding: 16px;
}

.v-card {
  margin-bottom: 16px;
  scroll-margin-top: 64px;
}
</style>