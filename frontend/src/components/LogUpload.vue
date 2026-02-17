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
        <div class="progress-ring">
          <svg viewBox="0 0 48 48">
            <circle cx="24" cy="24" r="20" fill="none" stroke="var(--color-border)" stroke-width="3"/>
            <circle cx="24" cy="24" r="20" fill="none" stroke="var(--color-primary)" stroke-width="3"
              stroke-linecap="round"
              :stroke-dasharray="126"
              :stroke-dashoffset="126 - (126 * Math.min(uploadProgress, 100)) / 100"
              style="transform: rotate(-90deg); transform-origin: center; transition: stroke-dashoffset 0.3s ease;"
            />
          </svg>
        </div>
        <p class="upload-status">Analyzing <strong>{{ fileName }}</strong></p>
        <p class="upload-percent">{{ Math.round(uploadProgress) }}%</p>
      </div>

      <div v-else class="upload-prompt">
        <div class="upload-icon-wrapper">
          <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <button @click="$refs.fileInput.click()" class="upload-btn">
          Choose File
        </button>
        <p class="upload-hint">or drag and drop a log file here</p>
        <p class="supported-formats">.log, .txt, .json up to 100 MB</p>
      </div>
    </div>

    <div v-if="error" class="error-message">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>{{ error }}</span>
      <button @click="error = null" class="dismiss-btn">&times;</button>
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

const MAX_FILE_SIZE = 100 * 1024 * 1024

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

const handleFileSelect = async (event) => {
  const file = event.target.files[0]
  if (file) {
    await uploadFile(file)
  }
}

const handleDrop = async (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    await uploadFile(file)
  }
}

const uploadFile = async (file) => {
  try {
    validateFile(file)

    uploading.value = true
    fileName.value = file.name
    uploadProgress.value = 0
    error.value = null

    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += Math.random() * 15
      }
    }, 200)

    const result = await analyzeLog(file)

    clearInterval(progressInterval)
    uploadProgress.value = 100

    emit('upload-complete', result)

    setTimeout(() => {
      router.push({ name: 'analysis', params: { id: result.id } })
    }, 500)

  } catch (err) {
    error.value = err.message || 'Upload failed'
    emit('upload-error', err)
  } finally {
    uploading.value = false
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}
</script>

<style scoped>
.upload-container {
  width: 100%;
  max-width: 560px;
  margin: 0 auto;
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--spacing-2xl) var(--spacing-lg);
  text-align: center;
  transition: all var(--transition-normal);
  background: var(--color-bg-secondary);
  cursor: pointer;
}

.drop-zone:hover {
  border-color: var(--color-border-hover);
  background: var(--color-bg-hover);
}

.drop-zone.drag-over {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
  transform: scale(1.01);
}

.drop-zone.uploading {
  pointer-events: none;
  border-style: solid;
  border-color: var(--color-primary);
}

.upload-icon-wrapper {
  margin-bottom: var(--spacing-md);
}

.upload-icon {
  width: 48px;
  height: 48px;
  color: var(--color-text-dim);
}

.upload-btn {
  background: var(--color-primary);
  color: white;
  border: none;
  padding: 10px 28px;
  border-radius: var(--radius-full);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.upload-btn:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.upload-hint {
  margin-top: 12px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.supported-formats {
  margin-top: 4px;
  font-size: 11px;
  color: var(--color-text-dim);
}

/* Upload Progress */
.upload-progress {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.progress-ring {
  width: 56px;
  height: 56px;
}

.progress-ring svg {
  width: 100%;
  height: 100%;
}

.upload-status {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-muted);
}

.upload-status strong {
  color: var(--color-text);
}

.upload-percent {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

/* Error */
.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--color-error-bg);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: 13px;
}

.dismiss-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 18px;
  padding: 0 4px;
  opacity: 0.7;
}

.dismiss-btn:hover {
  opacity: 1;
}
</style>
