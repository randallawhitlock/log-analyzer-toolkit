<template>
  <div class="level-chart">
    <h3 class="chart-title">{{ title }}</h3>
    
    <div class="chart-container">
      <div 
        v-for="level in orderedLevels" 
        :key="level.name"
        class="level-bar"
      >
        <div class="bar-label">
          <span class="level-icon">{{ level.icon }}</span>
          <span class="level-name">{{ level.name }}</span>
          <span class="level-count">{{ level.count.toLocaleString() }}</span>
        </div>
        <div class="bar-container">
          <div 
            class="bar-fill" 
            :class="`level-${level.name.toLowerCase()}`"
            :style="{ width: level.percentage + '%' }"
          ></div>
        </div>
        <span class="bar-percentage">{{ level.percentage.toFixed(1) }}%</span>
      </div>
    </div>
    
    <div v-if="!hasData" class="no-data">
      No severity data available
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  levelCounts: {
    type: Object,
    default: () => ({})
  },
  title: {
    type: String,
    default: 'Severity Breakdown'
  }
})

const levelConfig = {
  CRITICAL: { icon: '🔴', order: 0 },
  ERROR: { icon: '🟠', order: 1 },
  WARNING: { icon: '🟡', order: 2 },
  INFO: { icon: '🟢', order: 3 },
  DEBUG: { icon: '⚪', order: 4 }
}

const total = computed(() => {
  return Object.values(props.levelCounts || {}).reduce((sum, v) => sum + v, 0)
})

const hasData = computed(() => total.value > 0)

const orderedLevels = computed(() => {
  const levels = []
  
  for (const [name, count] of Object.entries(props.levelCounts || {})) {
    const config = levelConfig[name] || { icon: '⚫', order: 5 }
    levels.push({
      name,
      count,
      percentage: total.value > 0 ? (count / total.value) * 100 : 0,
      icon: config.icon,
      order: config.order
    })
  }
  
  return levels
    .filter(l => l.count > 0)
    .sort((a, b) => a.order - b.order)
})
</script>

<style scoped>
.level-chart {
  background: var(--color-bg-secondary, #1a1a2e);
  border-radius: 12px;
  border: 1px solid var(--color-border, #3a3a55);
  padding: 20px;
}

.chart-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text, #fff);
}

.chart-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.level-bar {
  display: grid;
  grid-template-columns: 140px 1fr 60px;
  align-items: center;
  gap: 12px;
}

.bar-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.level-icon {
  font-size: 14px;
}

.level-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-muted, #aaa);
  text-transform: uppercase;
}

.level-count {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text, #fff);
  margin-left: auto;
}

.bar-container {
  height: 12px;
  background: var(--color-bg-tertiary, #2a2a4e);
  border-radius: 6px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.5s ease;
}

.bar-percentage {
  font-size: 13px;
  color: var(--color-text-muted, #888);
  text-align: right;
}

/* Level colors */
.level-critical { background: linear-gradient(90deg, #ff4444, #cc0000); }
.level-error { background: linear-gradient(90deg, #ff9800, #f57c00); }
.level-warning { background: linear-gradient(90deg, #ffeb3b, #ffc107); }
.level-info { background: linear-gradient(90deg, #4caf50, #388e3c); }
.level-debug { background: linear-gradient(90deg, #9e9e9e, #757575); }

.no-data {
  text-align: center;
  color: var(--color-text-muted, #888);
  padding: 24px;
}
</style>
