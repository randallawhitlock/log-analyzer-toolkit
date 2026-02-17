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
          <span class="level-dot" :class="`dot-${level.name.toLowerCase()}`"></span>
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
  CRITICAL: { order: 0 },
  ERROR: { order: 1 },
  WARNING: { order: 2 },
  INFO: { order: 3 },
  DEBUG: { order: 4 }
}

const total = computed(() => {
  return Object.values(props.levelCounts || {}).reduce((sum, v) => sum + v, 0)
})

const hasData = computed(() => total.value > 0)

const orderedLevels = computed(() => {
  const levels = []

  for (const [name, count] of Object.entries(props.levelCounts || {})) {
    const config = levelConfig[name] || { order: 5 }
    levels.push({
      name,
      count,
      percentage: total.value > 0 ? (count / total.value) * 100 : 0,
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
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  padding: 20px;
}

.chart-title {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.chart-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.level-bar {
  display: grid;
  grid-template-columns: 130px 1fr 50px;
  align-items: center;
  gap: 12px;
}

.bar-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.level-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-critical { background: #ef4444; }
.dot-error { background: #f97316; }
.dot-warning { background: #eab308; }
.dot-info { background: #22c55e; }
.dot-debug { background: #71717a; }

.level-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.level-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}

.bar-container {
  height: 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.bar-percentage {
  font-size: 12px;
  color: var(--color-text-dim);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Level colors */
.level-critical { background: linear-gradient(90deg, #ef4444, #dc2626); }
.level-error { background: linear-gradient(90deg, #f97316, #ea580c); }
.level-warning { background: linear-gradient(90deg, #eab308, #ca8a04); }
.level-info { background: linear-gradient(90deg, #22c55e, #16a34a); }
.level-debug { background: linear-gradient(90deg, #71717a, #52525b); }

.no-data {
  text-align: center;
  color: var(--color-text-dim);
  padding: 24px;
  font-size: 13px;
}
</style>
