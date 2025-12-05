import { ref, computed } from 'vue'
import { useApi } from './useApi'

// Available model options
export interface ModelOption {
  name: string
  size: string
  description: string
  family: 'gemma3' | 'qwen3' | 'llama' | 'mistral'
}

// Fixed list of available models (must match backend)
export const AVAILABLE_MODELS: ModelOption[] = [
  { name: 'gemma3:1b', size: '~815MB', description: 'Small, fast model - best for quick responses', family: 'gemma3' },
  { name: 'qwen3:1.7b', size: '~1.4GB', description: 'Slightly larger, slower model - better quality responses', family: 'qwen3' },
  { name: 'ministral-3:3b', size: '~3GB', description: 'Mistral\'s compact model - balanced performance', family: 'mistral' },
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
