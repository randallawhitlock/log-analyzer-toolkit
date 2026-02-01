/**
 * Composable for API calls to the Log Analyzer backend.
 * Provides reactive state and methods for log analysis operations.
 */

import { ref } from 'vue'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Composable for interacting with the Log Analyzer API.
 * @returns {Object} API methods and reactive state
 */
export function useApi() {
    const loading = ref(false)
    const error = ref(null)

    /**
     * Upload and analyze a log file.
     * @param {File} file - The log file to analyze
     * @param {string} format - Log format (default: 'auto')
     * @param {number} maxErrors - Maximum errors to collect (default: 100)
     * @returns {Promise<Object>} Analysis result
     */
    const analyzeLog = async (file, format = 'auto', maxErrors = 100) => {
        loading.value = true
        error.value = null

        try {
            const formData = new FormData()
            formData.append('file', file)

            const response = await axios.post(
                `${API_BASE}/api/v1/analyze`,
                formData,
                {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    params: { format, max_errors: maxErrors }
                }
            )

            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    /**
     * Get list of analyses with pagination.
     * @param {Object} options - Pagination options
     * @returns {Promise<Object>} Paginated analyses list
     */
    const getAnalyses = async ({ skip = 0, limit = 20, format = null } = {}) => {
        loading.value = true
        error.value = null

        try {
            const params = { skip, limit }
            if (format) params.format = format

            const response = await axios.get(`${API_BASE}/api/v1/analyses`, { params })
            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    /**
     * Get a specific analysis by ID.
     * @param {string} id - Analysis UUID
     * @returns {Promise<Object>} Analysis details
     */
    const getAnalysis = async (id) => {
        loading.value = true
        error.value = null

        try {
            const response = await axios.get(`${API_BASE}/api/v1/analysis/${id}`)
            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    /**
     * Delete an analysis by ID.
     * @param {string} id - Analysis UUID
     * @returns {Promise<Object>} Success message
     */
    const deleteAnalysis = async (id) => {
        loading.value = true
        error.value = null

        try {
            const response = await axios.delete(`${API_BASE}/api/v1/analysis/${id}`)
            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    /**
     * Run AI triage on an analysis.
     * @param {string} analysisId - Analysis UUID
     * @param {string|null} provider - AI provider (anthropic, gemini, ollama)
     * @returns {Promise<Object>} Triage results
     */
    const runTriage = async (analysisId, provider = null) => {
        loading.value = true
        error.value = null

        try {
            const response = await axios.post(`${API_BASE}/api/v1/triage`, {
                analysis_id: analysisId,
                provider
            })
            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    /**
     * Get a specific triage by ID.
     * @param {string} id - Triage UUID
     * @returns {Promise<Object>} Triage details
     */
    const getTriage = async (id) => {
        loading.value = true
        error.value = null

        try {
            const response = await axios.get(`${API_BASE}/api/v1/triage/${id}`)
            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    /**
     * Get all triages for an analysis.
     * @param {string} analysisId - Analysis UUID
     * @returns {Promise<Array>} List of triages
     */
    const getTriagesForAnalysis = async (analysisId) => {
        loading.value = true
        error.value = null

        try {
            const response = await axios.get(`${API_BASE}/api/v1/analysis/${analysisId}/triages`)
            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    /**
     * Get list of supported log formats.
     * @returns {Promise<Object>} List of formats
     */
    const getFormats = async () => {
        try {
            const response = await axios.get(`${API_BASE}/api/v1/formats`)
            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        }
    }

    /**
     * Check API health.
     * @returns {Promise<Object>} Health status
     */
    const checkHealth = async () => {
        try {
            const response = await axios.get(`${API_BASE}/health`)
            return response.data
        } catch (err) {
            error.value = err.response?.data?.detail || err.message
            throw err
        }
    }

    return {
        loading,
        error,
        analyzeLog,
        getAnalyses,
        getAnalysis,
        deleteAnalysis,
        runTriage,
        getTriage,
        getTriagesForAnalysis,
        getFormats,
        checkHealth
    }
}
