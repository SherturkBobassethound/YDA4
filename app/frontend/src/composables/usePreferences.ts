import { ref, computed } from 'vue'
import { useApi } from './useApi'

// Available model options
export interface ModelOption {
  name: string
  size: string
  description: string
  family: 'gemma3' | 'qwen3' | 'llama'
}

export const AVAILABLE_MODELS: ModelOption[] = [
  // Gemma 3 models
  { name: 'gemma3:1b', size: '~1GB', description: 'Smallest Gemma - fastest responses', family: 'gemma3' },
  { name: 'gemma3:4b', size: '~4GB', description: 'Balanced Gemma - good quality and speed', family: 'gemma3' },
  { name: 'gemma3:12b', size: '~12GB', description: 'Large Gemma - high quality', family: 'gemma3' },
  { name: 'gemma3:27b', size: '~27GB', description: 'Largest Gemma - best quality', family: 'gemma3' },

  // Qwen 3 models
  { name: 'qwen3:1.7b', size: '~1.7GB', description: 'Smallest Qwen - very fast', family: 'qwen3' },
  { name: 'qwen3:4b', size: '~4GB', description: 'Balanced Qwen - good quality', family: 'qwen3' },
  { name: 'qwen3:8b', size: '~8GB', description: 'Mid-size Qwen - excellent balance', family: 'qwen3' },
  { name: 'qwen3:14b', size: '~14GB', description: 'Large Qwen - very high quality', family: 'qwen3' },
  { name: 'qwen3:30b', size: '~30GB', description: 'Largest Qwen - exceptional quality', family: 'qwen3' },

  // Legacy Llama models (for backward compatibility)
  { name: 'llama3.2:1b', size: '~1.3GB', description: 'Legacy - lightweight', family: 'llama' },
  { name: 'llama3.2:3b', size: '~3GB', description: 'Legacy - balanced', family: 'llama' },
  { name: 'llama3:8b', size: '~4.7GB', description: 'Legacy - high quality', family: 'llama' },
]

interface UserPreferences {
  preferred_model: string
  updated_at?: string
}

const preferredModel = ref<string>('gemma3:1b')
const isLoading = ref<boolean>(false)
const error = ref<string | null>(null)

export function usePreferences() {
  const { fetchWithAuth, API_BASE_URL } = useApi()

  /**
   * Get model information by name
   */
  const getModelInfo = (modelName: string): ModelOption | undefined => {
    return AVAILABLE_MODELS.find(m => m.name === modelName)
  }

  /**
   * Get the current preferred model
   */
  const getCurrentModel = computed(() => preferredModel.value)

  /**
   * Load user preferences from the backend
   */
  const loadPreferences = async (): Promise<void> => {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/user/preferences`)

      if (!response.ok) {
        throw new Error(`Failed to load preferences: ${response.statusText}`)
      }

      const data: UserPreferences = await response.json()
      preferredModel.value = data.preferred_model || 'gemma3:1b'
    } catch (err) {
      console.error('Error loading preferences:', err)
      error.value = err instanceof Error ? err.message : 'Failed to load preferences'
      // Use default on error
      preferredModel.value = 'gemma3:1b'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Save user preferences to the backend
   */
  const savePreferences = async (model: string): Promise<boolean> => {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/user/preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          preferred_model: model,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to save preferences: ${response.statusText}`)
      }

      const data: UserPreferences = await response.json()
      preferredModel.value = data.preferred_model
      return true
    } catch (err) {
      console.error('Error saving preferences:', err)
      error.value = err instanceof Error ? err.message : 'Failed to save preferences'
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update the preferred model and save to backend
   */
  const setPreferredModel = async (model: string): Promise<boolean> => {
    // Validate model exists
    if (!AVAILABLE_MODELS.find(m => m.name === model)) {
      error.value = `Invalid model: ${model}`
      return false
    }

    const success = await savePreferences(model)
    if (success) {
      preferredModel.value = model
    }
    return success
  }

  return {
    preferredModel: getCurrentModel,
    isLoading: computed(() => isLoading.value),
    error: computed(() => error.value),
    availableModels: AVAILABLE_MODELS,
    getModelInfo,
    loadPreferences,
    savePreferences,
    setPreferredModel,
  }
}
