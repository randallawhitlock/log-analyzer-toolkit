<template>
  <div id="app">
    <nav class="main-nav">
      <router-link to="/" class="nav-brand">
        <div class="brand-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect x="2" y="3" width="20" height="18" rx="3" stroke="currentColor" stroke-width="1.5" fill="none"/>
            <path d="M6 9h4M6 13h8M6 17h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="18" cy="9" r="2" fill="var(--color-primary)"/>
          </svg>
        </div>
        <span class="brand-text">Log Analyzer <span class="brand-accent">Pro</span></span>
      </router-link>

      <div class="nav-links">
        <router-link to="/" class="nav-link" exact-active-class="active">Home</router-link>
        <router-link to="/analyses" class="nav-link" active-class="active">Analyses</router-link>
        <router-link to="/upload" class="nav-link upload-link">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Upload
        </router-link>
        <ThemeToggle />
      </div>
    </nav>

    <main class="main-content">
      <router-view />
    </main>

    <footer class="main-footer">
      <p>Log Analyzer Toolkit v0.2.1</p>
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
  padding: 0 var(--spacing-lg);
  height: 56px;
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-border);
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

.brand-logo {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
}

.brand-text {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-accent {
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
}

.nav-link {
  padding: 6px 14px;
  text-decoration: none;
  color: var(--color-text-muted);
  border-radius: var(--radius-md);
  font-weight: 500;
  font-size: 13px;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--color-text);
  background: var(--color-bg-hover);
}

.nav-link.active {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.upload-link {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-primary);
  color: white !important;
  margin-left: 8px;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.upload-link:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.main-content {
  flex: 1;
}

.main-footer {
  text-align: center;
  padding: var(--spacing-lg);
  color: var(--color-text-dim);
  font-size: 12px;
  border-top: 1px solid var(--color-border);
}

.main-footer p {
  margin: 0;
}
</style>
