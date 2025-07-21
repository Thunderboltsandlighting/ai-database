<template>
  <div class="file-uploader">
    <v-file-input
      v-model="files"
      :label="label"
      :accept="accept"
      :prepend-icon="prependIcon"
      :multiple="multiple"
      :show-size="showSize"
      :counter="counter"
      :chips="chips"
      :truncate-length="truncateLength"
      @update:model-value="handleFileChange"
    ></v-file-input>
    
    <v-btn
      :color="buttonColor"
      :loading="uploading"
      :disabled="!files.length"
      @click="uploadFiles"
      class="mt-2"
    >
      {{ buttonText }}
    </v-btn>
    
    <div v-if="error" class="error-message mt-2">
      <v-alert type="error" dense>{{ error }}</v-alert>
    </div>
    
    <div v-if="progress > 0 && progress < 100" class="progress-bar mt-2">
      <v-progress-linear
        v-model="progress"
        :color="progressColor"
        height="10"
      ></v-progress-linear>
      <div class="text-center mt-1">{{ progress }}%</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FileUploader',
  props: {
    label: {
      type: String,
      default: 'Select Files'
    },
    accept: {
      type: String,
      default: undefined
    },
    prependIcon: {
      type: String,
      default: 'mdi-file-upload'
    },
    multiple: {
      type: Boolean,
      default: false
    },
    showSize: {
      type: Boolean,
      default: true
    },
    counter: {
      type: Boolean,
      default: true
    },
    chips: {
      type: Boolean,
      default: true
    },
    truncateLength: {
      type: [Number, String],
      default: 15
    },
    buttonText: {
      type: String,
      default: 'Upload'
    },
    buttonColor: {
      type: String,
      default: 'primary'
    },
    progressColor: {
      type: String,
      default: 'primary'
    },
    uploadUrl: {
      type: String,
      required: true
    },
    extraData: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      files: [],
      uploading: false,
      progress: 0,
      error: null
    };
  },
  methods: {
    handleFileChange(files) {
      this.files = files;
      this.error = null;
      this.progress = 0;
      this.$emit('files-changed', files);
    },
    
    async uploadFiles() {
      if (!this.files.length) return;
      
      this.uploading = true;
      this.progress = 0;
      this.error = null;
      
      try {
        const formData = new FormData();
        
        // Add files to form data
        if (this.multiple) {
          for (let i = 0; i < this.files.length; i++) {
            formData.append('files[]', this.files[i]);
          }
        } else {
          formData.append('file', this.files[0]);
        }
        
        // Add extra data
        Object.keys(this.extraData).forEach(key => {
          formData.append(key, this.extraData[key]);
        });
        
        // Upload files
        const response = await this.uploadWithProgress(formData);
        
        // Reset after successful upload
        this.progress = 100;
        setTimeout(() => {
          this.progress = 0;
          this.files = [];
        }, 2000);
        
        // Emit upload success event
        this.$emit('upload-success', response.data);
      } catch (error) {
        this.error = error.response?.data?.message || error.message || 'Upload failed';
        this.$emit('upload-error', this.error);
      } finally {
        this.uploading = false;
      }
    },
    
    uploadWithProgress(formData) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            this.progress = Math.round((event.loaded / event.total) * 100);
          }
        });
        
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = {
                data: JSON.parse(xhr.responseText),
                status: xhr.status,
                statusText: xhr.statusText
              };
              resolve(response);
            } catch (e) {
              reject(new Error('Invalid response format'));
            }
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        });
        
        xhr.addEventListener('error', () => {
          reject(new Error('Network error'));
        });
        
        xhr.addEventListener('abort', () => {
          reject(new Error('Upload aborted'));
        });
        
        xhr.open('POST', this.uploadUrl);
        xhr.send(formData);
      });
    }
  }
};
</script>

<style scoped>
.file-uploader {
  width: 100%;
}

.error-message {
  margin: 8px 0;
}

.progress-bar {
  margin: 8px 0;
}
</style>