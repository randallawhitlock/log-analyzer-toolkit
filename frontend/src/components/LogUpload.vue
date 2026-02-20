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

      <!-- Uploading State -->
      <div v-if="uploading" class="upload-progress fade-in">
        <div class="progress-wrapper">
          <svg class="progress-ring" viewBox="0 0 120 120">
            <circle class="ring-bg" cx="60" cy="60" r="54" />
            <circle class="ring-fill" cx="60" cy="60" r="54"
              :stroke-dasharray="339.29"
              :stroke-dashoffset="339.29 - (339.29 * Math.min(uploadProgress, 100)) / 100" />
          </svg>
          <div class="progress-text">
            <span class="percent">{{ Math.round(uploadProgress) }}%</span>
          </div>
        </div>
        <div class="processing-details">
          <p class="status-msg">Analyzing <strong class="file-name">{{ fileName }}</strong></p>
          <p class="status-sub">Extracting metadata and finding errors...</p>
        </div>
      </div>

      <!-- Idle State -->
      <div v-else class="upload-prompt fade-in">
        <div class="upload-icon-wrapper" :class="{ 'pulse': isDragging }">
          <div class="icon-ring-1"></div>
          <div class="icon-ring-2"></div>
          <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <button @click="$refs.fileInput.click()" class="btn-primary upload-btn">
          Select Log File
        </button>
        <p class="upload-hint">or drag and drop here</p>
        <div class="supported-formats">
          <span class="badge">.log</span>
          <span class="badge">.txt</span>
          <span class="badge">.json</span>
          <span class="limit">• Max 100MB</span>
        </div>
      </div>
    </div>

    <!-- Error Toast -->
    <transition name="toast">
      <div v-if="error" class="error-toast">
        <div class="error-icon">⚠️</div>
        <span class="error-text">{{ error }}</span>
        <button @click="error = null" class="dismiss-btn">&times;</button>
      </div>
    </transition>
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

    // Simulate progress smoothly
    const progressInterval = setInterval(() => {
      // Slow down as it approaches 90%
      const remaining = 90 - uploadProgress.value
      if (remaining > 0) {
        uploadProgress.value += Math.max(0.5, remaining * 0.1)
      }
    }, 150)

    const result = await analyzeLog(file)

    clearInterval(progressInterval)
    uploadProgress.value = 100

    emit('upload-complete', result)

    setTimeout(() => {
      router.push({ name: 'analysis', params: { id: result.id } })
    }, 600)

  } catch (err) {
    error.value = err.message || 'Upload failed'
    emit('upload-error', err)
  } finally {
    setTimeout(() => {
      uploading.value = false
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }, 600) // Keep 100% visible briefly
  }
}
</script>

<style scoped>
.upload-container {
  width: 100%;
  max-width: 640px;
  margin: 0 auto;
  position: relative;
}

.drop-zone {
  position: relative;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--spacing-3xl) var(--spacing-xl);
  text-align: center;
  transition: all var(--transition-spring);
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  cursor: pointer;
  overflow: hidden;
}

.drop-zone::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(circle at center, var(--color-primary-light) 0%, transparent 70%);
  opacity: 0;
  transition: opacity var(--transition-normal);
  pointer-events: none;
}

.drop-zone:hover {
  border-color: var(--color-primary);
  background: var(--color-bg-elevated);
}

.drop-zone:hover::before {
  opacity: 0.5;
}

.drop-zone.drag-over {
  border-color: var(--color-primary);
  background: var(--color-bg-elevated);
  transform: scale(1.02);
  box-shadow: var(--shadow-glow);
}

.drop-zone.drag-over::before {
  opacity: 1;
}

.drop-zone.uploading {
  pointer-events: none;
  border-style: solid;
  border-color: var(--color-border-hover);
}

/* Upload Prompt Elements */
.upload-icon-wrapper {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  box-shadow: inset 0 2px 4px rgba(255,255,255,0.05);
  transition: all var(--transition-spring);
}

.drop-zone:hover .upload-icon-wrapper {
  transform: translateY(-4px);
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.upload-icon {
  width: 32px;
  height: 32px;
  color: var(--color-text-dim);
  transition: color var(--transition-fast);
  position: relative;
  z-index: 2;
}

.drop-zone:hover .upload-icon {
  color: var(--color-primary);
}

/* Animated Pulse Rings */
.icon-ring-1, .icon-ring-2 {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  border-radius: 50%;
  border: 2px solid var(--color-primary);
  opacity: 0;
  pointer-events: none;
}

.upload-icon-wrapper.pulse .icon-ring-1 {
  animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
}
.upload-icon-wrapper.pulse .icon-ring-2 {
  animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
  animation-delay: 0.75s;
}

@keyframes ping {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(2); opacity: 0; }
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-hover));
  color: white;
  padding: 12px 32px;
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: 1rem;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

.upload-hint {
  margin-top: 16px;
  color: var(--color-text); /* Maximum contrast */
  font-size: 0.95rem;
  font-weight: 500;
}

.supported-formats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
}

.badge {
  background: var(--color-bg-tertiary);
  color: var(--color-text); /* Lightened to primary text color */
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-family: var(--font-mono);
  font-weight: 500;
}

.limit {
  font-size: 0.75rem;
  color: var(--color-text); /* Maximum contrast */
  font-weight: 500;
  margin-left: 4px;
}

/* Upload Progress Element */
.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-lg);
}

.progress-wrapper {
  position: relative;
  width: 120px;
  height: 120px;
}

.progress-ring {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: var(--color-bg-tertiary);
  stroke-width: 8;
}

.ring-fill {
  fill: none;
  stroke: var(--color-primary);
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-text {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.percent {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}

.processing-details {
  text-align: center;
}

.status-msg {
  font-size: 1.125rem;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.file-name {
  color: var(--color-text);
  font-weight: 600;
}

.status-sub {
  font-size: 0.875rem;
  color: var(--color-primary);
  animation: pulse 2s infinite;
}

/* Transitions */
.fade-in {
  animation: fadeIn var(--transition-normal) both;
}

.toast-enter-active,
.toast-leave-active {
  transition: all var(--transition-spring);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.error-toast {
  position: absolute;
  bottom: -60px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: rgba(244, 63, 94, 0.1);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(244, 63, 94, 0.3);
  border-radius: var(--radius-full);
  color: var(--color-error);
  font-size: 0.875rem;
  font-weight: 500;
  box-shadow: var(--shadow-glow-error);
  white-space: nowrap;
}

.error-icon {
  font-size: 1.1rem;
}

.dismiss-btn {
  background: none;
  border: none;
  color: inherit;
  font-size: 1.25rem;
  line-height: 1;
  padding: 0 4px;
  opacity: 0.7;
  cursor: pointer;
}
.dismiss-btn:hover {
  opacity: 1;
}
</style>
