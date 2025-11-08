import { useAuth } from './useAuth'

// Get API base URLs from environment or use container-aware defaults
const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8000'
    }
    return `${window.location.protocol}//${window.location.hostname}:8000`
  }
  return 'http://backend:8000'
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getApiBaseUrl()

export function useApi() {
  const { getAuthToken } = useAuth()

  /**
   * Make an authenticated API request
   */
  const fetchWithAuth = async (url: string, options: RequestInit = {}): Promise<Response> => {
    const token = await getAuthToken()

    const headers = new Headers(options.headers)

    // Add authorization header if token exists
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    // Merge headers back into options
    const requestOptions: RequestInit = {
      ...options,
      headers,
    }

    return fetch(url, requestOptions)
  }

  return {
    fetchWithAuth,
    API_BASE_URL,
  }
}
