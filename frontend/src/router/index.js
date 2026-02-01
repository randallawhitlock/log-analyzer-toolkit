/**
 * Vue Router configuration for Log Analyzer Pro.
 */

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        name: 'home',
        component: () => import('../views/HomeView.vue'),
        meta: { title: 'Log Analyzer Pro' }
    },
    {
        path: '/analysis/:id',
        name: 'analysis',
        component: () => import('../views/AnalysisView.vue'),
        meta: { title: 'Analysis Details' },
        props: true
    },
    {
        path: '/upload',
        name: 'upload',
        component: () => import('../views/UploadView.vue'),
        meta: { title: 'Upload Log File' }
    },
    {
        path: '/analyses',
        name: 'analyses',
        component: () => import('../views/AnalysesListView.vue'),
        meta: { title: 'All Analyses' }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Update document title on navigation
router.beforeEach((to, from, next) => {
    document.title = to.meta.title || 'Log Analyzer Pro'
    next()
})

export default router
