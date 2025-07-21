<template>
  <div class="upload-view">
    <h1>File Upload & Import</h1>

    <v-alert type="info" class="mb-4">
      This page allows you to upload and import CSV files into the database. You can also browse and import CSV files from the existing CSV folder structure.
    </v-alert>
    
    <v-tabs v-model="activeTab">
      <v-tab value="upload">Upload New Files</v-tab>
      <v-tab value="csv-folder">Browse CSV Folder</v-tab>
    </v-tabs>
    
    <v-window v-model="activeTab" class="mt-4">
      <v-window-item value="upload">
    
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Upload Files</v-card-title>
          <v-card-text>
            <v-file-input
              v-model="files"
              label="Select CSV Files"
              accept=".csv"
              prepend-icon="mdi-file-upload"
              multiple
              show-size
              counter
              chips
              truncate-length="15"
            ></v-file-input>
            
            <v-btn
              color="primary"
              :loading="uploading"
              :disabled="!files.length"
              @click="uploadFiles"
              class="mt-2"
            >
              Upload Files
            </v-btn>
          </v-card-text>
        </v-card>
        
        <v-card class="mt-4">
          <v-card-title>Import Settings</v-card-title>
          <v-card-text>
            <v-select
              v-model="importSettings.targetTable"
              :items="availableTables"
              label="Target Table"
              placeholder="Select a table"
              :disabled="!selectedFile"
            ></v-select>
            
            <v-checkbox
              v-model="importSettings.detectFormat"
              label="Auto-detect format"
              :disabled="!selectedFile"
            ></v-checkbox>
            
            <v-checkbox
              v-model="importSettings.skipHeader"
              label="Skip header row"
              :disabled="!selectedFile || importSettings.detectFormat"
            ></v-checkbox>
            
            <v-select
              v-model="importSettings.delimiter"
              :items="delimiters"
              label="CSV Delimiter"
              :disabled="!selectedFile || importSettings.detectFormat"
            ></v-select>
            
            <v-btn
              color="success"
              :disabled="!selectedFile || !importSettings.targetTable"
              :loading="importing"
              @click="importFile"
              class="mt-2"
            >
              Import File
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="6">
        <v-card class="mb-4">
          <v-card-title>Uploaded Files</v-card-title>
          <v-card-text>
            <div v-if="uploadedFiles.length === 0" class="text-center pa-4 text-grey">
              No files uploaded yet
            </div>
            <v-list v-else>
              <v-list-item
                v-for="(file, index) in uploadedFiles"
                :key="index"
                @click="selectFile(file)"
                :active="selectedFile && selectedFile.id === file.id"
              >
                <template v-slot:prepend>
                  <v-icon>mdi-file-delimited</v-icon>
                </template>
                <v-list-item-title>{{ file.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ formatFileSize(file.size) }} | {{ file.uploadedAt }}
                </v-list-item-subtitle>
                <template v-slot:append>
                  <v-btn icon @click.stop="previewFile(file)">
                    <v-icon>mdi-eye</v-icon>
                  </v-btn>
                  <v-btn icon @click.stop="deleteFile(file)">
                    <v-icon>mdi-delete</v-icon>
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
        
        <v-card v-if="selectedFile">
          <v-card-title>File Preview: {{ selectedFile.name }}</v-card-title>
          <v-card-text>
            <div v-if="filePreview.loading" class="text-center pa-4">
              <v-progress-circular indeterminate></v-progress-circular>
              <div class="mt-2">Loading preview...</div>
            </div>
            <div v-else-if="filePreview.error" class="error-message">
              <v-alert type="error">{{ filePreview.error }}</v-alert>
            </div>
            <div v-else>
              <v-simple-table v-if="filePreview.headers.length > 0">
                <template v-slot:default>
                  <thead>
                    <tr>
                      <th v-for="(header, index) in filePreview.headers" :key="index">
                        {{ header }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rowIndex) in filePreview.rows" :key="rowIndex">
                      <td v-for="(header, colIndex) in filePreview.headers" :key="colIndex">
                        {{ row[colIndex] }}
                      </td>
                    </tr>
                  </tbody>
                </template>
              </v-simple-table>
            </div>
            
            <v-card v-if="filePreview.formatDetection" class="mt-4">
              <v-card-title>Format Detection Results</v-card-title>
              <v-card-text>
                <v-list-item>
                  <v-list-item-title>Detected Format:</v-list-item-title>
                  <v-list-item-subtitle>{{ filePreview.formatDetection.format }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Confidence Score:</v-list-item-title>
                  <v-list-item-subtitle>{{ filePreview.formatDetection.confidence }}%</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Delimiter:</v-list-item-title>
                  <v-list-item-subtitle>{{ filePreview.formatDetection.delimiter }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Has Header:</v-list-item-title>
                  <v-list-item-subtitle>{{ filePreview.formatDetection.hasHeader ? 'Yes' : 'No' }}</v-list-item-subtitle>
                </v-list-item>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    </v-window-item>
    
    <v-window-item value="csv-folder">
      <CsvFolderBrowser @error="showSnackbar($event, 'error')" @file-imported="onFileImported" />
    </v-window-item>
    </v-window>
    
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
import { useFilesStore } from '../stores';
import CsvFolderBrowser from '../components/CsvFolderBrowser.vue';

export default {
  name: 'UploadView',
  components: {
    CsvFolderBrowser
  },
  data() {
    return {
      files: [],
      uploadedFiles: [],
      selectedFile: null,
      uploading: false,
      importing: false,
      availableTables: ['providers', 'payments', 'monthly_summaries', 'knowledge_base'],
      delimiters: [
        { text: 'Comma (,)', value: ',' },
        { text: 'Semicolon (;)', value: ';' },
        { text: 'Tab (\\t)', value: '\t' },
        { text: 'Pipe (|)', value: '|' }
      ],
      importSettings: {
        targetTable: '',
        detectFormat: true,
        skipHeader: true,
        delimiter: ','
      },
      filePreview: {
        headers: [],
        rows: [],
        loading: false,
        error: null,
        formatDetection: null
      },
      snackbar: {
        show: false,
        text: '',
        color: 'success'
      },
      activeTab: 'csv-folder' // Default to CSV folder tab
    };
  },
  methods: {
    async uploadFiles() {
      if (!this.files.length) return;
      
      this.uploading = true;
      
      try {
        // In real implementation, use store
        // const filesStore = useFilesStore();
        
        // For demo, simulate upload
        setTimeout(() => {
          for (const file of this.files) {
            const uploadedFile = {
              id: Date.now() + Math.floor(Math.random() * 1000),
              name: file.name,
              size: file.size,
              uploadedAt: new Date().toLocaleString(),
              path: `/uploads/${file.name}`
            };
            
            this.uploadedFiles.push(uploadedFile);
          }
          
          this.showSnackbar('Files uploaded successfully', 'success');
          this.files = [];
          this.uploading = false;
          
          // Select the first uploaded file
          if (this.uploadedFiles.length > 0 && !this.selectedFile) {
            this.selectFile(this.uploadedFiles[0]);
          }
        }, 1000);
      } catch (error) {
        this.showSnackbar(`Error uploading files: ${error.message}`, 'error');
        this.uploading = false;
      }
    },
    
    selectFile(file) {
      this.selectedFile = file;
      this.importSettings.targetTable = '';
      this.loadFilePreview(file);
    },
    
    async loadFilePreview(file) {
      this.filePreview.loading = true;
      this.filePreview.error = null;
      
      try {
        // In real implementation, fetch preview from API
        // const response = await axios.get(`/api/files/preview/${file.id}`);
        
        // For demo, simulate preview
        setTimeout(() => {
          if (file.name.includes('provider')) {
            this.filePreview.headers = ['id', 'name', 'specialty', 'address', 'phone', 'active'];
            this.filePreview.rows = [
              ['1', 'Tammy Maxey', 'Mental Health', '123 Main St', '555-123-4567', 'true'],
              ['2', 'Dustin Nisley', 'Therapy', '456 Oak Ave', '555-234-5678', 'true'],
              ['3', 'Sidney Snipes', 'Counseling', '789 Pine Rd', '555-345-6789', 'true'],
              ['4', 'Isabel Rehak', 'Psychology', '101 Elm St', '555-456-7890', 'true'],
              ['5', 'Kailani Ameele', 'Therapy', '202 Maple Dr', '555-567-8901', 'true']
            ];
            
            this.filePreview.formatDetection = {
              format: 'Provider Information',
              confidence: 92,
              delimiter: ',',
              hasHeader: true
            };
            
            this.importSettings.targetTable = 'providers';
          } else if (file.name.includes('payment')) {
            this.filePreview.headers = ['id', 'provider_id', 'amount', 'date', 'payer', 'claim_id'];
            this.filePreview.rows = [
              ['1', '1', '1250.00', '2025-07-01', 'Medicare', 'CLM12345'],
              ['2', '2', '875.50', '2025-07-02', 'Blue Cross', 'CLM23456'],
              ['3', '1', '950.75', '2025-07-03', 'Aetna', 'CLM34567'],
              ['4', '3', '1100.25', '2025-07-03', 'Cigna', 'CLM45678'],
              ['5', '2', '750.00', '2025-07-04', 'Medicare', 'CLM56789']
            ];
            
            this.filePreview.formatDetection = {
              format: 'Payment Transaction',
              confidence: 95,
              delimiter: ',',
              hasHeader: true
            };
            
            this.importSettings.targetTable = 'payments';
          } else {
            this.filePreview.headers = ['Column 1', 'Column 2', 'Column 3'];
            this.filePreview.rows = [
              ['Data 1', 'Data 2', 'Data 3'],
              ['Data 4', 'Data 5', 'Data 6'],
              ['Data 7', 'Data 8', 'Data 9']
            ];
            
            this.filePreview.formatDetection = {
              format: 'Unknown',
              confidence: 45,
              delimiter: ',',
              hasHeader: true
            };
          }
          
          this.filePreview.loading = false;
        }, 800);
      } catch (error) {
        this.filePreview.error = error.message;
        this.filePreview.loading = false;
      }
    },
    
    previewFile(file) {
      this.selectFile(file);
    },
    
    deleteFile(file) {
      // In real implementation, delete from server
      // const filesStore = useFilesStore();
      // await filesStore.deleteFile(file.id);
      
      // For demo, just remove from array
      const index = this.uploadedFiles.findIndex(f => f.id === file.id);
      if (index !== -1) {
        this.uploadedFiles.splice(index, 1);
      }
      
      if (this.selectedFile && this.selectedFile.id === file.id) {
        this.selectedFile = null;
        this.filePreview.headers = [];
        this.filePreview.rows = [];
        this.filePreview.formatDetection = null;
      }
      
      this.showSnackbar('File deleted', 'info');
    },
    
    async importFile() {
      if (!this.selectedFile || !this.importSettings.targetTable) return;
      
      this.importing = true;
      
      try {
        // In real implementation, use store
        // const filesStore = useFilesStore();
        // await filesStore.importFile(this.selectedFile.id, this.importSettings);
        
        // For demo, simulate import
        setTimeout(() => {
          this.showSnackbar(`File ${this.selectedFile.name} imported successfully to ${this.importSettings.targetTable} table`, 'success');
          this.importing = false;
        }, 1200);
      } catch (error) {
        this.showSnackbar(`Error importing file: ${error.message}`, 'error');
        this.importing = false;
      }
    },
    
    formatFileSize(bytes) {
      const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
      if (bytes === 0) return '0 Bytes';
      const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
      return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
    },
    
    showSnackbar(text, color) {
      this.snackbar.text = text;
      this.snackbar.color = color;
      this.snackbar.show = true;
    },
    
    onFileImported(data) {
      const { file, result } = data;
      
      if (result.success) {
        this.showSnackbar(`Successfully imported ${file.name} with ${result.records_successful} records`, 'success');
      } else {
        this.showSnackbar(`Failed to import ${file.name}: ${result.error}`, 'error');
      }
    }
  }
};
</script>

<style scoped>
.upload-view {
  padding: 16px;
}

.error-message {
  margin: 16px 0;
}
</style>