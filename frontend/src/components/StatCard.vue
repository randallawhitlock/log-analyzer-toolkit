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
    default: null
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
  gap: 14px;
  padding: 16px 20px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  transition: all var(--transition-normal);
}

.stat-card:hover {
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-sm);
}

.stat-icon {
  font-size: 20px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.stat-label {
  font-size: 11px;
  color: var(--color-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.stat-subtitle {
  font-size: 11px;
  color: var(--color-text-dim);
}

/* Color variants */
.color-success .stat-value { color: var(--color-success); }
.color-warning .stat-value { color: var(--color-warning); }
.color-error .stat-value { color: var(--color-error); }
.color-info .stat-value { color: var(--color-info); }

.color-success .stat-icon { background: var(--color-success-light); }
.color-warning .stat-icon { background: var(--color-warning-light); }
.color-error .stat-icon { background: var(--color-error-light); }
.color-info .stat-icon { background: var(--color-info-light); }
</style>
