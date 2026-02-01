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
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
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
    default: null // 'number', 'percent', 'bytes'
  }
})

const colorClass = computed(() => `color-${props.color}`)

const formattedValue = computed(() => {
  const val = props.value
  
  if (props.format === 'number' && typeof val === 'number') {
    return val.toLocaleString()
  }
  
  if (props.format === 'percent' && typeof val === 'number') {
    return `${val.toFixed(1)}%`
  }
  
  if (props.format === 'bytes' && typeof val === 'number') {
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
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--color-bg-secondary, #1a1a2e);
  border-radius: 12px;
  border: 1px solid var(--color-border, #3a3a55);
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: var(--color-border-hover, #5a5a7a);
  transform: translateY(-2px);
}

.stat-icon {
  font-size: 24px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary, #2a2a4e);
  border-radius: 10px;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 13px;
  color: var(--color-text-muted, #888);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text, #fff);
}

.stat-subtitle {
  font-size: 12px;
  color: var(--color-text-dim, #666);
}

/* Color variants */
.color-success .stat-value {
  color: var(--color-success, #4caf50);
}

.color-warning .stat-value {
  color: var(--color-warning, #ff9800);
}

.color-error .stat-value {
  color: var(--color-error, #f44336);
}

.color-info .stat-value {
  color: var(--color-info, #2196f3);
}

.color-success .stat-icon {
  background: rgba(76, 175, 80, 0.15);
}

.color-warning .stat-icon {
  background: rgba(255, 152, 0, 0.15);
}

.color-error .stat-icon {
  background: rgba(244, 67, 54, 0.15);
}

.color-info .stat-icon {
  background: rgba(33, 150, 243, 0.15);
}
</style>
