<template>
  <div class="profile-container">
    <button class="profile-button" @click="handleClick">
      <span v-if="!loading">{{ displayInitials }}</span>
      <span v-else class="loading">•••</span>
    </button>

    <!-- Dropdown menu when logged in -->
    <div v-if="showMenu && isAuthenticated" class="dropdown-menu" @click.stop>
      <div class="menu-item user-info">
        <div class="user-email">{{ userEmail }}</div>
      </div>
      <div class="menu-divider"></div>
      <button class="menu-item" @click="handleSignOut">
        Sign Out
      </button>
    </div>

    <!-- Auth Modal -->
    <AuthModal :is-open="showAuthModal" @close="showAuthModal = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'
import AuthModal from './AuthModal.vue'

const { isAuthenticated, userInitials, userEmail, loading, signOut, initAuth } = useAuth()

const showAuthModal = ref(false)
const showMenu = ref(false)

const displayInitials = computed(() => {
  if (isAuthenticated.value) {
    return userInitials.value
  }
  return '?'
})

const handleClick = () => {
  if (isAuthenticated.value) {
    showMenu.value = !showMenu.value
  } else {
    showAuthModal.value = true
  }
}

const handleSignOut = async () => {
  await signOut()
  showMenu.value = false
}

// Close menu when clicking outside
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.closest('.profile-container')) {
    showMenu.value = false
  }
}

onMounted(async () => {
  await initAuth()
  document.addEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.profile-container {
  position: relative;
}

.profile-button {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 999;
  background: rgb(237, 161, 9);
  border: none;
  color: #000;
  font-weight: 600;
  font-size: 16px;

  /* make it a perfect circle: */
  width: 50px;
  height: 50px;
  padding: 0;               /* no extra padding */
  border-radius: 50%;

  /* center initials inside: */
  display: flex;
  align-items: center;
  justify-content: center;

  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  transition: all 0.2s;
}

.profile-button:hover {
  background: rgb(255, 180, 30);
  transform: scale(1.05);
}

.loading {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.dropdown-menu {
  position: fixed;
  top: 80px;
  right: 20px;
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  z-index: 998;
  min-width: 200px;
  overflow: hidden;
}

.menu-item {
  padding: 12px 16px;
  background: none;
  border: none;
  color: #fff;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: background 0.2s;
  font-size: 14px;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.menu-item.user-info {
  cursor: default;
  padding: 12px 16px;
}

.menu-item.user-info:hover {
  background: none;
}

.user-email {
  color: #999;
  font-size: 13px;
  word-break: break-all;
}

.menu-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
}
</style>