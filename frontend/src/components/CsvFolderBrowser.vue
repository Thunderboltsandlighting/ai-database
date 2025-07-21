<template>
  <div class="csv-folder-browser">
    <v-card>
      <v-card-title>
        <div class="d-flex align-center">
          <v-icon class="mr-2">mdi-folder-open</v-icon>
          <span>CSV Folder</span>
        </div>
        <v-spacer></v-spacer>
        <v-btn icon @click="refreshFiles">
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
      </v-card-title>
      
      <v-card-text>
        <v-alert
          v-if="error"
          type="error"
          class="mb-4"
          density="compact"
        >
          {{ error }}
        </v-alert>
        
        <div v-if="loading" class="d-flex justify-center align-center pa-4">
          <v-progress-circular indeterminate></v-progress-circular>
          <span class="ml-2">Loading files...</span>
        </div>
        
        <!-- Folder structure breadcrumb -->
        <div v-if="folders.length > 0 || files.length > 0" class="folder-breadcrumb mb-4">
          <v-breadcrumbs :items="breadcrumbs" divider="/">
            <template v-slot:item="{ item }">
              <v-breadcrumbs-item
                :to="item.to"
                :disabled="item.disabled"
                @click="navigateToFolder(item)"
              >
                <v-icon v-if="item.path === ''" class="mr-1">mdi-folder-home</v-icon>
                <v-icon v-else class="mr-1">mdi-folder</v-icon>
                {{ item.title }}
              </v-breadcrumbs-item>
            </template>
          </v-breadcrumbs>
        </div>
        
        <div v-else-if="folders.length === 0 && files.length === 0" class="text-center pa-4">
          <v-icon size="large" color="grey">mdi-folder-open-outline</v-icon>
          <div class="text-body-1 text-grey mt-2">No CSV files found in the folder structure</div>
        </div>
        
        <div v-else>
          <!-- Folder tree structure -->
          <v-treeview
            v-model="selectedFolder"
            :items="folderTree"
            item-children="children"
            item-text="name"
            open-all
            activatable
            return-object
            @update:model-value="onFolderSelected"
          >
            <template v-slot:prepend="{ item }">
              <v-icon v-if="item.type === 'folder'">
                {{ item.open ? 'mdi-folder-open' : 'mdi-folder' }}
              </v-icon>
              <v-icon v-else-if="item.type === 'file'" color="primary">
                mdi-file-delimited
              </v-icon>
            </template>
          </v-treeview>
          
          <!-- File list for selected folder -->
          <v-expansion-panels v-if="folderFiles.length > 0" class="mt-4">
            <v-expansion-panel v-for="file in folderFiles" :key="file.full_path">
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon class="mr-2">mdi-file-delimited</v-icon>
                  <span>{{ file.name }}</span>
                  <v-chip class="ml-2" size="small" color="primary" text-color="white">
                    {{ formatFileSize(file.size) }}
                  </v-chip>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="d-flex justify-space-between align-center mb-3">
                  <div>
                    <div><strong>Path:</strong> {{ file.folder }}/{{ file.name }}</div>
                    <div><strong>Modified:</strong> {{ file.modified }}</div>
                  </div>
                  <div>
                    <v-btn
                      color="primary"
                      variant="outlined"
                      class="mr-2"
                      @click="previewFile(file)"
                      :loading="previewLoading === file.full_path"
                    >
                      <v-icon start>mdi-eye</v-icon>
                      Preview
                    </v-btn>
                    <v-btn
                      color="success"
                      @click="importFile(file)"
                      :loading="importLoading === file.full_path"
                    >
                      <v-icon start>mdi-database-import</v-icon>
                      Import to Database
                    </v-btn>
                  </div>
                </div>
                
                <!-- Preview section -->
                <v-card v-if="file.preview" class="mt-3" variant="outlined">
                  <v-card-title>File Preview</v-card-title>
                  <v-card-text>
                    <v-table dense>
                      <thead>
                        <tr>
                          <th v-for="(header, index) in file.preview.headers" :key="index">
                            {{ header }}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, rowIndex) in file.preview.rows" :key="rowIndex">
                          <td v-for="(cell, cellIndex) in row" :key="cellIndex">
                            {{ cell }}
                          </td>
                        </tr>
                      </tbody>
                    </v-table>
                    <div class="text-caption text-grey mt-2">
                      Showing {{ file.preview.rows.length }} of {{ file.preview.total_rows }} rows
                    </div>
                  </v-card-text>
                </v-card>
                
                <!-- Import result section -->
                <v-alert
                  v-if="file.importResult"
                  :type="file.importResult.success ? 'success' : 'error'"
                  class="mt-3"
                  :icon="file.importResult.success ? 'mdi-check-circle' : 'mdi-alert-circle'"
                >
                  <div v-if="file.importResult.success">
                    <div class="d-flex align-center mb-2">
                      <strong class="text-h6">Import Successful</strong>
                      <v-chip class="ml-2" color="success" size="small">{{ file.importResult.records_successful }} records</v-chip>
                    </div>
                    <v-divider class="mb-2"></v-divider>
                    <div class="d-flex flex-wrap">
                      <v-chip class="ma-1" variant="outlined">
                        <v-icon start>mdi-database</v-icon>
                        Processed: {{ file.importResult.records_processed }}
                      </v-chip>
                      <v-chip class="ma-1" variant="outlined" color="success">
                        <v-icon start>mdi-check</v-icon>
                        Successful: {{ file.importResult.records_successful }}
                      </v-chip>
                      <v-chip v-if="file.importResult.records_failed > 0" class="ma-1" variant="outlined" color="error">
                        <v-icon start>mdi-close</v-icon>
                        Failed: {{ file.importResult.records_failed }}
                      </v-chip>
                      <v-chip v-if="file.importResult.issues_count > 0" class="ma-1" variant="outlined" color="warning">
                        <v-icon start>mdi-alert</v-icon>
                        Issues: {{ file.importResult.issues_count }}
                      </v-chip>
                    </div>
                  </div>
                  <div v-else>
                    <div class="d-flex align-center mb-2">
                      <strong class="text-h6">Import Failed</strong>
                    </div>
                    <v-divider class="mb-2"></v-divider>
                    <div class="error-message">{{ file.importResult.error }}</div>
                    <div class="mt-2">
                      <v-btn small text color="primary" @click="retryImport(file)">
                        <v-icon start>mdi-refresh</v-icon>
                        Retry Import
                      </v-btn>
                    </div>
                  </div>
                </v-alert>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
import axios from 'axios';

// API client
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5001/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

export default {
  name: 'CsvFolderBrowser',
  data() {
    return {
      loading: false,
      error: null,
      folders: [],
      files: [],
      selectedFolder: null,
      previewLoading: null,
      importLoading: null
    };
  },
  computed: {
    // Create a tree structure for the folders and files
    folderTree() {
      const tree = [];
      
      // Add folders
      for (const folder of this.folders) {
        const parts = folder.path.split('/');
        let currentLevel = tree;
        
        for (let i = 0; i < parts.length; i++) {
          if (parts[i] === '.') continue;
          
          // Find or create the folder in the current level
          let found = currentLevel.find(item => item.name === parts[i] && item.type === 'folder');
          
          if (!found) {
            found = {
              id: folder.path,
              name: parts[i],
              type: 'folder',
              path: parts.slice(0, i + 1).join('/'),
              children: []
            };
            currentLevel.push(found);
          }
          
          currentLevel = found.children;
        }
      }
      
      // Return the tree structure
      return tree;
    },
    
    // Files in the selected folder
    folderFiles() {
      if (!this.selectedFolder) {
        return this.files;
      }
      
      return this.files.filter(file => {
        // If file.folder starts with the selected folder path
        return file.folder === this.selectedFolder.path;
      });
    },
    
    // Breadcrumb navigation items
    breadcrumbs() {
      const items = [
        {
          title: 'CSV Folder',
          disabled: false,
          path: '',
          to: '#'
        }
      ];
      
      if (this.selectedFolder && this.selectedFolder.path) {
        const parts = this.selectedFolder.path.split('/');
        let currentPath = '';
        
        for (let i = 0; i < parts.length; i++) {
          if (parts[i] === '.') continue;
          
          currentPath = currentPath ? `${currentPath}/${parts[i]}` : parts[i];
          
          items.push({
            title: parts[i],
            disabled: i === parts.length - 1, // Disable the current folder
            path: currentPath,
            to: '#'
          });
        }
      }
      
      return items;
    }
  },
  methods: {
    async refreshFiles() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await apiClient.get('/files-bridge/csv-folder');
        
        this.folders = response.data.folders;
        this.files = response.data.files;
        
        // Auto-select the first folder if none selected
        if (!this.selectedFolder && this.folders.length > 0) {
          this.selectedFolder = this.folderTree[0];
        }
      } catch (error) {
        this.error = `Error loading CSV files: ${error.message}`;
        console.error('Error loading CSV files:', error);
      } finally {
        this.loading = false;
      }
    },
    
    onFolderSelected(folder) {
      // If the selected item is a file, extract its folder
      if (folder && folder.type === 'file') {
        const file = this.files.find(f => f.full_path === folder.id);
        if (file) {
          // Find the parent folder in the tree
          for (const f of this.folders) {
            if (file.folder.startsWith(f.path)) {
              this.selectedFolder = {
                id: f.path,
                name: f.name,
                type: 'folder',
                path: f.path,
                children: []
              };
              break;
            }
          }
        }
      }
    },
    
    async previewFile(file) {
      if (file.preview) {
        // Toggle preview if already loaded
        file.preview = null;
        return;
      }
      
      this.previewLoading = file.full_path;
      
      try {
        const response = await apiClient.post('/files-bridge/preview-csv-file', {
          file_path: file.full_path,
          max_rows: 5
        });
        
        // Vue reactivity - using Object.assign to add new property
        // Vue reactivity for adding new property
        if (typeof this.$set === 'function') {
          // Vue 2 style
          this.$set(file, 'preview', response.data);
        } else {
          // Vue 3 style
          file.preview = response.data;
        }
      } catch (error) {
        console.error('Error previewing file:', error);
        this.$emit('error', `Error previewing file: ${error.message}`);
      } finally {
        this.previewLoading = null;
      }
    },
    
    async importFile(file) {
      this.importLoading = file.full_path;
      
      try {
        const response = await apiClient.post('/files-bridge/import-csv-file', {
          file_path: file.full_path
        });
        
        // Vue reactivity - using Object.assign to add new property
        // Vue reactivity for adding new property
        if (typeof this.$set === 'function') {
          // Vue 2 style
          this.$set(file, 'importResult', response.data);
        } else {
          // Vue 3 style
          file.importResult = response.data;
        }
        
        // Emit event to notify parent component
        this.$emit('file-imported', {
          file: file,
          result: response.data
        });
      } catch (error) {
        console.error('Error importing file:', error);
        
        // Set error result
        // Vue reactivity for adding new property
        if (typeof this.$set === 'function') {
          // Vue 2 style
          this.$set(file, 'importResult', {
            success: false,
            error: error.response?.data?.message || error.message
          });
        } else {
          // Vue 3 style
          file.importResult = {
            success: false,
            error: error.response?.data?.message || error.message
          };
        }
        
        this.$emit('error', `Error importing file: ${error.message}`);
      } finally {
        this.importLoading = null;
      }
    },
    
    navigateToFolder(item) {
      if (item.disabled || !item.path) {
        // If it's the root or current folder, do nothing
        if (item.path === '') {
          this.selectedFolder = null;  // Select root
        }
        return;
      }
      
      // Find the folder object in the folders array
      const folder = this.folders.find(f => f.path === item.path);
      
      if (folder) {
        // Set the selected folder
        this.selectedFolder = {
          id: folder.path,
          name: folder.name,
          type: 'folder',
          path: folder.path,
          children: []
        };
      }
    },
    
    retryImport(file) {
      // Clear previous import result
      if (typeof this.$set === 'function') {
        this.$set(file, 'importResult', null);
      } else {
        file.importResult = null;
      }
      
      // Retry import
      this.importFile(file);
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
  },
  mounted() {
    this.refreshFiles();
  }
};
</script>

<style scoped>
.csv-folder-browser {
  max-height: 100%;
}
</style>