<template>
  <div class="chat-container">
    <!-- Message for logged-out users -->
    <div v-if="!isAuthenticated" class="logged-out-message">
      <p>Please log in to start using YODA.</p>
    </div>

    <!-- Chat Section -->
    <div v-if="isAuthenticated" class="chat-section">
      <!-- Model Selection -->
      <div class="model-selection">
        <label for="model-select">AI Model:</label>
        <select id="model-select" v-model="selectedModel" @change="onModelChange">
          <option v-for="model in availableModels" :key="model.name" :value="model.name">
            {{ model.name }} ({{ model.size }})
          </option>
        </select>
        <span class="model-info">{{ getModelDescription(selectedModel) }}</span>
      </div>

      <!-- Transcription Summary (only shown when content is processed) -->
      <div v-if="hasTranscription" class="transcription-summary">
        <h4>Summary</h4>
        <p>{{ summary }}</p>
        <button @click="toggleTranscription" class="toggle-btn">
          {{ showFullTranscription ? 'Hide' : 'Show' }} Full Transcription
        </button>
        <div v-if="showFullTranscription" class="full-transcription">
          <p>{{ transcription }}</p>
        </div>
      </div>

      <!-- Chat Messages -->
      <div class="messages-container" ref="messagesContainer">
        <!-- Welcome message when no messages -->
        <div v-if="messages.length === 0" class="empty-state-message">
          <p>Welcome to YODA! Ask questions about your sources, or add a podcast/YouTube URL from the sidebar to get started.</p>
        </div>

        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="[
            'message',
            msg.sender === 'user' ? 'message-user' : 'message-machine'
          ]"
        >
          <p>{{ msg.text }}</p>
          <span v-if="msg.sender === 'machine'" class="model-tag">{{ msg.model }}</span>
        </div>
      </div>

      <!-- Chat Input -->
      <div class="input-container">
        <input
          type="text"
          v-model="newMessage"
          placeholder="Ask questions about your sources..."
          @keyup.enter="sendMessage"
          :disabled="isProcessing"
        />
        <button @click="sendMessage" :disabled="isProcessing || !newMessage.trim()">
          {{ isProcessing ? 'Thinking...' : 'Send' }}
        </button>
      </div>

      <!-- Reset Button (only shown when content is processed) -->
      <div v-if="hasTranscription" class="reset-section">
        <button @click="reset" class="reset-btn">Process New Audio</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue';
import { useApi } from '../composables/useApi'
import { useAuth } from '../composables/useAuth'

interface Message {
  sender: 'user' | 'machine';
  text: string;
  model?: string;
}

interface ModelInfo {
  name: string;
  size: string;
  description: string;
}

const { fetchWithAuth, API_BASE_URL } = useApi()
const { isAuthenticated } = useAuth()

// State
const messages = ref<Message[]>([]);
const newMessage = ref('');
const messagesContainer = ref<HTMLElement>();

// Chat processing state
const isProcessing = ref(false);

// Transcription state
const hasTranscription = ref(false);
const transcription = ref('');
const summary = ref('');
const showFullTranscription = ref(false);

// Model selection state
const selectedModel = ref('llama3.2:1b'); // Default lightweight model
const availableModels = ref<ModelInfo[]>([
  { name: 'llama3.2:1b', size: '~1.3GB', description: 'Lightweight, fast responses' },
  { name: 'llama3.2:3b', size: '~3GB', description: 'Better quality, balanced performance' },
  { name: 'llama3:8b', size: '~4.7GB', description: 'High quality, slower responses' }
]);

// Fetch available models on component mount
onMounted(async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/models`, {
      signal: AbortSignal.timeout(10000)
    });

    if (response.ok) {
      const data = await response.json();
      if (data.models && Array.isArray(data.models)) {
        // Update available models with actual installed models
        const installedModels = data.models.map((model: any) => ({
          name: model.name,
          size: model.size ? formatBytes(model.size) : 'Unknown',
          description: getModelDescription(model.name)
        }));

        if (installedModels.length > 0) {
          availableModels.value = installedModels;
          // Set first available model as default if current selection not available
          if (!installedModels.find((m: ModelInfo) => m.name === selectedModel.value)) {
            selectedModel.value = installedModels[0].name;
          }
        }
      }
    }
  } catch (error) {
    console.warn('Could not fetch available models, using defaults:', error);
  }
});

// Helper functions
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const getModelDescription = (modelName: string): string => {
  const descriptions: Record<string, string> = {
    'llama3.2:1b': 'Lightweight, fast responses',
    'llama3.2:3b': 'Better quality, balanced performance', 
    'llama3:8b': 'High quality, slower responses',
    'codellama:7b': 'Specialized for code tasks',
    'default': 'General purpose model'
  };
  return descriptions[modelName] || descriptions.default;
};

const onModelChange = () => {
  console.log('Model changed to:', selectedModel.value);
};

// Handle transcription data from Sidebar
const handleTranscriptionComplete = (data: { transcription: string; summary: string }) => {
  transcription.value = data.transcription;
  summary.value = data.summary;
  hasTranscription.value = true;

  // Add welcome message
  messages.value.push({
    sender: 'machine',
    text: `Great! I've processed your content using ${selectedModel.value}. You can now ask me questions about it. What would you like to know?`,
    model: selectedModel.value
  });
};

const sendMessage = async () => {
  const txt = newMessage.value.trim();
  if (!txt) return;

  messages.value.push({ sender: 'user', text: txt });
  newMessage.value = '';
  scrollToBottom();

  isProcessing.value = true;

  try {
    // Send request to backend - context is optional now since backend always searches vector DB
    const requestBody: any = {
      message: txt,
      model: selectedModel.value
    };

    // Include context only if available (for fallback purposes)
    if (transcription.value) {
      requestBody.context = transcription.value;
    }

    const response = await fetchWithAuth(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
      signal: AbortSignal.timeout(120000) // 2 minute timeout for chat
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || 'Failed to get chat response');
    }

    const data = await response.json();
    messages.value.push({
      sender: 'machine',
      text: data.response,
      model: selectedModel.value
    });

  } catch (error: any) {
    console.error('Error sending message:', error);
    let errorMessage = 'Sorry, I encountered an error. Please try again.';
    if (error.name === 'TimeoutError') {
      errorMessage = 'The response is taking longer than expected. Please try asking a simpler question or try again.';
    }
    messages.value.push({
      sender: 'machine',
      text: errorMessage,
      model: selectedModel.value
    });
  } finally {
    isProcessing.value = false;
    scrollToBottom();
  }
};

const toggleTranscription = () => {
  showFullTranscription.value = !showFullTranscription.value;
};

const reset = () => {
  hasTranscription.value = false;
  transcription.value = '';
  summary.value = '';
  messages.value = [];
  showFullTranscription.value = false;
};

const scrollToBottom = async () => {
  await nextTick();
  const el = messagesContainer.value;
  if (el) el.scrollTop = el.scrollHeight;
};

// Expose the handler for parent component
defineExpose({
  handleTranscriptionComplete
});
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background-color: #ffffff;
}

.logged-out-message {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 1.1rem;
}

.logged-out-message p {
  margin: 0;
}

/* Model Selection Styles */
.model-selection {
  padding: 15px 20px;
  background-color: #f1f3f5;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.model-selection label {
  font-weight: 500;
  color: #333;
}

.model-selection select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background-color: white;
  font-size: 0.9rem;
  min-width: 180px;
}

.model-selection select:focus {
  outline: none;
  border-color: #007bff;
}

.model-info {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
}

/* Message model tag */
.model-tag {
  font-size: 0.7rem;
  color: #666;
  margin-top: 4px;
  display: block;
  font-style: italic;
}

/* Initial State Styles */
.initial-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.welcome-card {
  background-color: #f8f9fa;
  border: 2px solid #dee2e6;
  border-radius: 12px;
  padding: 40px;
  max-width: 500px;
  width: 100%;
  text-align: center;
}

.welcome-card h3 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 1.5rem;
}

.welcome-card p {
  margin: 0 0 25px 0;
  color: #666;
  line-height: 1.6;
}

.instructions {
  text-align: left;
  background-color: #ffffff;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.instructions h4 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 1.1rem;
}

.instructions ol {
  margin: 0;
  padding-left: 20px;
  color: #666;
  line-height: 1.8;
}

.instructions li {
  margin-bottom: 8px;
}

/* Chat Section Styles */
.chat-section {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.transcription-summary {
  padding: 20px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.transcription-summary h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.transcription-summary p {
  margin: 0 0 15px 0;
  color: #666;
  line-height: 1.6;
}

.toggle-btn {
  background-color: #6c757d;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.toggle-btn:hover {
  background-color: #5a6268;
}

.full-transcription {
  margin-top: 15px;
  padding: 15px;
  background-color: #ffffff;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
}

.full-transcription p {
  margin: 0;
  color: #495057;
  line-height: 1.6;
  font-size: 0.9rem;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.empty-state-message {
  text-align: center;
  padding: 40px 20px;
  color: #666;
  font-size: 1.1rem;
}

.empty-state-message p {
  margin: 0;
  line-height: 1.6;
}

.message {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
}

.message-user {
  align-self: flex-end;
  background-color: #007bff;
  color: white;
}

.message-machine {
  align-self: flex-start;
  background-color: #e9ecef;
  color: #333;
}

.message p {
  margin: 0;
  line-height: 1.4;
}

.input-container {
  padding: 20px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 10px;
}

.input-container input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  outline: none;
}

.input-container input:focus {
  border-color: #007bff;
}

.input-container button {
  padding: 12px 24px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.input-container button:hover:not(:disabled) {
  background-color: #0056b3;
}

.input-container button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.reset-section {
  padding: 20px;
  text-align: center;
  border-top: 1px solid #e9ecef;
}

.reset-btn {
  padding: 10px 20px;
  background-color: #dc3545;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.reset-btn:hover {
  background-color: #c82333;
}

@media (max-width: 768px) {
  .model-selection {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .model-selection select {
    width: 100%;
    min-width: unset;
  }
}
</style>