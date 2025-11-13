<template>
  <div v-if="isOpen" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <button class="close-btn" @click="closeModal">&times;</button>

      <h2>{{ isLogin ? 'Login' : 'Sign Up' }}</h2>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            placeholder="your.email@example.com"
            autocomplete="email"
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            placeholder="••••••••"
            :autocomplete="isLogin ? 'current-password' : 'new-password'"
          />
        </div>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>

        <button type="submit" class="submit-btn" :disabled="isLoading">
          {{ isLoading ? 'Please wait...' : (isLogin ? 'Login' : 'Sign Up') }}
        </button>
      </form>

      <div class="toggle-mode">
        <button @click="toggleMode" class="toggle-btn">
          {{ isLogin ? 'Need an account? Sign up' : 'Already have an account? Login' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAuth } from '../composables/useAuth'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const { signIn, signUp } = useAuth()

const isLogin = ref(true)
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const isLoading = ref(false)

const toggleMode = () => {
  isLogin.value = !isLogin.value
  errorMessage.value = ''
  successMessage.value = ''
}

const closeModal = () => {
  emit('close')
  // Reset form
  setTimeout(() => {
    email.value = ''
    password.value = ''
    errorMessage.value = ''
    successMessage.value = ''
    isLogin.value = true
  }, 300)
}

const handleSubmit = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  isLoading.value = true

  try {
    if (isLogin.value) {
      const { error } = await signIn(email.value, password.value)
      if (error) {
        errorMessage.value = error.message
      } else {
        successMessage.value = 'Login successful!'
        setTimeout(() => {
          closeModal()
        }, 1000)
      }
    } else {
      const { error } = await signUp(email.value, password.value)
      if (error) {
        errorMessage.value = error.message
      } else {
        successMessage.value = 'Account created! Please check your email to verify your account.'
        email.value = ''
        password.value = ''
        // Switch to login mode after successful signup
        setTimeout(() => {
          isLogin.value = true
          successMessage.value = ''
        }, 3000)
      }
    }
  } catch (error) {
    errorMessage.value = 'An unexpected error occurred'
  } finally {
    isLoading.value = false
  }
}

// Reset form when modal closes
watch(() => props.isOpen, (newVal) => {
  if (!newVal) {
    email.value = ''
    password.value = ''
    errorMessage.value = ''
    successMessage.value = ''
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #1a1a1a;
  border-radius: 12px;
  padding: 32px;
  width: 90%;
  max-width: 400px;
  position: relative;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: #999;
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.close-btn:hover {
  color: #fff;
}

h2 {
  margin: 0 0 24px 0;
  color: #fff;
  font-size: 24px;
  font-weight: 600;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #ccc;
  font-size: 14px;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 12px;
  background: #2a2a2a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: rgb(237, 161, 9);
}

input::placeholder {
  color: #666;
}

.error-message {
  padding: 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #ef4444;
  font-size: 14px;
  margin-bottom: 16px;
}

.success-message {
  padding: 12px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 8px;
  color: #22c55e;
  font-size: 14px;
  margin-bottom: 16px;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  background: rgb(237, 161, 9);
  color: #000;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: rgb(255, 180, 30);
  transform: translateY(-1px);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-mode {
  margin-top: 20px;
  text-align: center;
}

.toggle-btn {
  background: none;
  border: none;
  color: rgb(237, 161, 9);
  font-size: 14px;
  cursor: pointer;
  text-decoration: underline;
  transition: color 0.2s;
}

.toggle-btn:hover {
  color: rgb(255, 180, 30);
}
</style>
