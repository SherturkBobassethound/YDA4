import { useAuth } from './useAuth'

// Get API base URLs from environment or use container-aware defaults
const getApiBaseUrl = (): string => {
  // In production, VITE_API_BASE_URL should be set at build time
  // Fallback logic for development/local environments
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8000'
    }
    // For Fly.io production, don't append port - use the full backend URL from env
    // This fallback is only for local Docker setups
    if (window.location.hostname.includes('.fly.dev')) {
      // In Fly.io, backend is on a different subdomain, so we need the env var
      console.warn('VITE_API_BASE_URL not set. Backend requests may fail.')
      return '' // Return empty to force error if not configured
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
