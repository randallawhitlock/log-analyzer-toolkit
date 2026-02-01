<template>
  <div class="upload-container">
    <div
      class="drop-zone"
      :class="{ 'drag-over': isDragging, 'uploading': uploading }"
      @drop.prevent="handleDrop"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
    >
      <input
        type="file"
        ref="fileInput"
        @change="handleFileSelect"
        accept=".log,.txt,.json"
        hidden
      />
      
      <div v-if="uploading" class="upload-progress">
        <div class="spinner"></div>
        <p>Analyzing {{ fileName }}...</p>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
        </div>
      </div>
      
      <div v-else class="upload-prompt">
        <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <button @click="$refs.fileInput.click()" class="upload-btn">
          Choose File
        </button>
        <p class="upload-hint">or drag and drop a log file here</p>
        <p class="supported-formats">Supports: .log, .txt, .json (up to 100MB)</p>
      </div>
    </div>
    
    <div v-if="error" class="error-message">
      <span class="error-icon">⚠️</span>
      {{ error }}
      <button @click="error = null" class="dismiss-btn">×</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '../composables/useApi'

const emit = defineEmits(['upload-complete', 'upload-error'])
const router = useRouter()
const { analyzeLog, loading: apiLoading, error: apiError } = useApi()

const fileInput = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const fileName = ref('')
const uploadProgress = ref(0)
const error = ref(null)

const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB

/**
 * Validate file before upload
 */
const validateFile = (file) => {
  if (!file) {
    throw new Error('No file selected')
  }
  
  if (file.size > MAX_FILE_SIZE) {
    throw new Error(`File too large. Maximum size is ${MAX_FILE_SIZE / (1024 * 1024)}MB`)
  }
  
  const allowedTypes = ['.log', '.txt', '.json']
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowedTypes.includes(ext)) {
    throw new Error(`Invalid file type. Supported: ${allowedTypes.join(', ')}`)
  }
  
  return true
}

/**
 * Handle file selection from input
 */
const handleFileSelect = async (event) => {
  const file = event.target.files[0]
  if (file) {
    await uploadFile(file)
  }
}

/**
 * Handle drag-and-drop
 */
const handleDrop = async (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    await uploadFile(file)
  }
}

/**
 * Upload and analyze file
 */
const uploadFile = async (file) => {
  try {
    validateFile(file)
    
    uploading.value = true
    fileName.value = file.name
    uploadProgress.value = 0
    error.value = null
    
    // Simulate progress (actual upload doesn't provide progress easily)
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += Math.random() * 15
      }
    }, 200)
    
    const result = await analyzeLog(file)
    
    clearInterval(progressInterval)
    uploadProgress.value = 100
    
    emit('upload-complete', result)
    
    // Navigate to analysis page
    setTimeout(() => {
      router.push({ name: 'analysis', params: { id: result.id } })
    }, 500)
    
  } catch (err) {
    error.value = err.message || 'Upload failed'
    emit('upload-error', err)
  } finally {
    uploading.value = false
    // Reset file input
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}
</script>

<style scoped>
.upload-container {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.drop-zone {
  border: 2px dashed var(--color-border, #3a3a55);
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  transition: all 0.3s ease;
  background: var(--color-bg-secondary, #1a1a2e);
  cursor: pointer;
}

.drop-zone:hover {
  border-color: var(--color-primary, #646cff);
  background: var(--color-bg-hover, #2a2a4e);
}

.drop-zone.drag-over {
  border-color: var(--color-primary, #646cff);
  background: var(--color-bg-hover, #2a2a4e);
  transform: scale(1.02);
}

.drop-zone.uploading {
  pointer-events: none;
}

.upload-icon {
  width: 64px;
  height: 64px;
  color: var(--color-text-muted, #888);
  margin-bottom: 16px;
}

.upload-btn {
  background: var(--color-primary, #646cff);
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-btn:hover {
  background: var(--color-primary-hover, #535bf2);
  transform: translateY(-2px);
}

.upload-hint {
  margin-top: 12px;
  color: var(--color-text-muted, #888);
}

.supported-formats {
  margin-top: 8px;
  font-size: 12px;
  color: var(--color-text-dim, #666);
}

.upload-progress {
  padding: 24px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-border, #3a3a55);
  border-top-color: var(--color-primary, #646cff);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-bar {
  height: 8px;
  background: var(--color-bg-tertiary, #2a2a4e);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 16px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary, #646cff), var(--color-success, #4caf50));
  border-radius: 4px;
  transition: width 0.3s ease;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--color-error-bg, rgba(244, 67, 54, 0.1));
  border: 1px solid var(--color-error, #f44336);
  border-radius: 8px;
  color: var(--color-error, #f44336);
}

.dismiss-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 18px;
  padding: 0 4px;
}
</style>
