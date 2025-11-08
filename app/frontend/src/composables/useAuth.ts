import { ref, computed } from 'vue'
import { supabase } from '../lib/supabaseClient'
import type { User, AuthError } from '@supabase/supabase-js'

const user = ref<User | null>(null)
const loading = ref(true)

export function useAuth() {
  const isAuthenticated = computed(() => !!user.value)

  // Get user initials from email
  const userInitials = computed(() => {
    if (!user.value?.email) return ''
    const email = user.value.email
    const name = email.split('@')[0]
    const parts = name.split(/[._-]/)

    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }
    return name.substring(0, 2).toUpperCase()
  })

  // Get user email
  const userEmail = computed(() => user.value?.email || '')

  // Get user ID
  const userId = computed(() => user.value?.id || '')

  // Initialize auth state
  const initAuth = async () => {
    loading.value = true
    try {
      const { data: { session } } = await supabase.auth.getSession()
      user.value = session?.user || null
    } catch (error) {
      console.error('Error getting session:', error)
    } finally {
      loading.value = false
    }

    // Listen for auth changes
    supabase.auth.onAuthStateChange((_event, session) => {
      user.value = session?.user || null
      loading.value = false
    })
  }

  // Sign up
  const signUp = async (email: string, password: string): Promise<{ error: AuthError | null }> => {
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
      })
      return { error }
    } catch (error) {
      return { error: error as AuthError }
    }
  }

  // Sign in
  const signIn = async (email: string, password: string): Promise<{ error: AuthError | null }> => {
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      return { error }
    } catch (error) {
      return { error: error as AuthError }
    }
  }

  // Sign out
  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) throw error
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  // Get auth token for API calls
  const getAuthToken = async (): Promise<string | null> => {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token || null
  }

  return {
    user,
    loading,
    isAuthenticated,
    userInitials,
    userEmail,
    userId,
    initAuth,
    signUp,
    signIn,
    signOut,
    getAuthToken,
  }
}
