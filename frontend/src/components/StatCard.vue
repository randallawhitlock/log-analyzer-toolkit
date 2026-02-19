<template>
  <div class="stat-card" :class="colorClass">
    <div class="stat-icon" v-if="icon">{{ icon }}</div>
    <div class="stat-content">
      <span class="stat-label">{{ title }}</span>
      <span class="stat-value">{{ formattedValue }}</span>
      <span v-if="subtitle" class="stat-subtitle">{{ subtitle }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    default: 0
  },
  subtitle: {
    type: String,
    default: null
  },
  icon: {
    type: String,
    default: null
  },
  color: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'success', 'warning', 'error', 'info'].includes(v)
  },
  format: {
    type: String,
    default: null
  },
  disableAnimation: {
    type: Boolean,
    default: false
  }
})

const colorClass = computed(() => `color-${props.color}`)

const displayValue = ref(0)
const isNumber = computed(() => typeof props.value === 'number')

const animateValue = (target) => {
  if (!isNumber.value || props.disableAnimation) {
    displayValue.value = target
    return
  }

  const start = displayValue.value
  const end = target
  const duration = 1200 // 1.2s spring-like duration
  let startTime = null

  const step = (timestamp) => {
    if (!startTime) startTime = timestamp
    const progress = Math.min((timestamp - startTime) / duration, 1)
    // easeOutExpo
    const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
    displayValue.value = start + (end - start) * ease
    if (progress < 1) {
      window.requestAnimationFrame(step)
    } else {
      displayValue.value = end
    }
  }
  window.requestAnimationFrame(step)
}

onMounted(() => {
  animateValue(props.value)
})

watch(() => props.value, (newVal) => {
  animateValue(newVal)
})

const formattedValue = computed(() => {
  const val = isNumber.value ? displayValue.value : props.value

  if (props.format === 'number' && isNumber.value) {
    return Math.round(val).toLocaleString()
  }

  if (props.format === 'percent' && isNumber.value) {
    return `${val.toFixed(1)}%`
  }

  if (props.format === 'bytes' && isNumber.value) {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = val
    let unitIndex = 0
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`
  }

  return val
})
</script>

<style scoped>
.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  transition: all var(--transition-spring);
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  opacity: 0.05;
  transition: opacity var(--transition-normal);
  z-index: 0;
  pointer-events: none;
}

.stat-card:hover {
  border-color: var(--color-border-hover);
  transform: translateY(-4px) scale(1.01);
  box-shadow: var(--shadow-md);
  background: var(--color-bg-elevated);
}

.stat-card:hover::before {
  opacity: 0.15;
}

/* Color specific backgrounds */
.color-success::before { background: radial-gradient(circle at top right, var(--color-success), transparent 70%); }
.color-warning::before { background: radial-gradient(circle at top right, var(--color-warning), transparent 70%); }
.color-error::before { background: radial-gradient(circle at top right, var(--color-error), transparent 70%); }
.color-info::before { background: radial-gradient(circle at top right, var(--color-info), transparent 70%); }

.stat-icon {
  position: relative;
  z-index: 1;
  font-size: 24px;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-lg);
  flex-shrink: 0;
  box-shadow: inset 0 2px 4px rgba(255,255,255,0.05);
}

.stat-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.stat-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-dim);
  margin-top: 2px;
}

/* Color variants */
.color-success .stat-value { color: var(--color-success); }
.color-warning .stat-value { color: var(--color-warning); }
.color-error .stat-value { color: var(--color-error); }
.color-info .stat-value { color: var(--color-info); }

.color-success .stat-icon { background: var(--color-success-light); color: var(--color-success); }
.color-warning .stat-icon { background: var(--color-warning-light); color: var(--color-warning); }
.color-error .stat-icon { background: var(--color-error-light); color: var(--color-error); }
.color-info .stat-icon { background: var(--color-info-light); color: var(--color-info); }
</style>
