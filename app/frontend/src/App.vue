<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatApp from './components/ChatApp.vue'
import ProfileButton from './components/ProfileButton.vue'
import { useAuth } from './composables/useAuth'

const { initAuth } = useAuth()

// Reference to ChatApp component to call its methods
const chatAppRef = ref<InstanceType<typeof ChatApp>>()

// Initialize authentication on app mount
onMounted(async () => {
  await initAuth()
})

// Handle transcription completion from Sidebar
const handleTranscriptionComplete = (data: { transcription: string; summary: string }) => {
  // Call the ChatApp method to handle the transcription data
  chatAppRef.value?.handleTranscriptionComplete(data)
}
</script>

<template>
  <div class="app-layout">
    <Sidebar @transcription-complete="handleTranscriptionComplete" />
    <div class="main-content">
      <ChatApp ref="chatAppRef" />
    </div>
    <teleport to="body">
      <ProfileButton />
    </teleport>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: #f5f5f5;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  border-left: 1px solid #e0e0e0;
}
</style>