<template>
  <div id="app">
    <nav class="main-nav">
      <router-link to="/" class="nav-brand">
        <span class="brand-icon">📊</span>
        <span class="brand-text">Log Analyzer <span class="brand-accent">Pro</span></span>
      </router-link>
      
      <div class="nav-links">
        <router-link to="/" class="nav-link">Home</router-link>
        <router-link to="/analyses" class="nav-link">Analyses</router-link>
        <router-link to="/upload" class="nav-link upload-link">+ Upload</router-link>
        <ThemeToggle />
      </div>
    </nav>

    <main class="main-content">
      <router-view />
    </main>

    <footer class="main-footer">
      <p>Log Analyzer Toolkit v0.1.0</p>
    </footer>
  </div>
</template>

<script setup>
import ThemeToggle from './components/ThemeToggle.vue'
</script>

<style scoped>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--color-bg-secondary, #1a1a2e);
  border-bottom: 1px solid var(--color-border, #3a3a55);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
}

.brand-icon {
  font-size: 28px;
}

.brand-text {
  font-size: 18px;
  font-weight: 700;
}

.brand-accent {
  background: linear-gradient(135deg, var(--color-primary, #646cff), var(--color-secondary, #9c27b0));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-link {
  padding: 8px 16px;
  text-decoration: none;
  color: var(--color-text-muted, #888);
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.nav-link:hover {
  color: var(--color-text, #fff);
  background: var(--color-bg-tertiary, #2a2a4e);
}

.nav-link.router-link-active {
  color: var(--color-primary, #646cff);
}

.upload-link {
  background: var(--color-primary, #646cff);
  color: white !important;
}

.upload-link:hover {
  background: var(--color-primary-hover, #535bf2);
}

.main-content {
  flex: 1;
}

.main-footer {
  text-align: center;
  padding: 24px;
  color: var(--color-text-dim, #555);
  font-size: 13px;
  border-top: 1px solid var(--color-border, #3a3a55);
}

.main-footer p {
  margin: 0;
}
</style>
