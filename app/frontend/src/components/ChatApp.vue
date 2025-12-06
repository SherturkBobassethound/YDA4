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
        <div class="summary-header">
          <h4>Summary</h4>
          <button @click="toggleSummary" class="toggle-btn-small">
            {{ showSummary ? 'Hide' : 'Show' }}
          </button>
        </div>
        <div v-if="showSummary" class="summary-content" v-html="renderMarkdown(summary)"></div>
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
          <div class="message-content" v-html="renderMarkdown(msg.text)"></div>
          <span v-if="msg.sender === 'machine'" class="model-tag">{{ msg.model }}</span>

          <!-- Display source citations if available (two-level collapsible) -->
          <div v-if="msg.sources && Object.keys(msg.sources).length > 0" class="sources">
            <div class="sources-toggle" @click="toggleSources(msg)">
              <span class="toggle-icon">{{ msg.sourcesExpanded ? '▼' : '►' }}</span>
              <span class="sources-header">Sources ({{ Object.keys(msg.sources).length }})</span>
            </div>

            <!-- Expandable sources list -->
            <div v-if="msg.sourcesExpanded" class="source-list">
              <div v-for="(sourceInfo, num) in msg.sources" :key="num" class="source-item">
                <div class="source-header" @click="toggleChunk(msg, num)">
                  <span class="chunk-toggle-icon">{{ isChunkExpanded(msg, num) ? '▼' : '►' }}</span>
                  <span class="source-number">[{{ num }}]</span>
                  <span class="source-title">{{ sourceInfo.title }}</span>
                </div>

                <!-- Expandable chunk content -->
                <div v-if="isChunkExpanded(msg, num)" class="chunk-content">
                  {{ sourceInfo.content }}
                </div>
              </div>
            </div>
          </div>
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
import { marked } from 'marked';
import { useApi } from '../composables/useApi'
import { useAuth } from '../composables/useAuth'
import { usePreferences, type ModelOption } from '../composables/usePreferences'

interface SourceInfo {
  title: string;
  content: string;
}

interface Message {
  sender: 'user' | 'machine';
  text: string;
  model?: string;
  sources?: Record<string, SourceInfo>; // Mapping of citation numbers to {title, content}
  sourcesExpanded?: boolean; // Track if sources section is expanded
  expandedChunks?: Set<string>; // Track which individual chunks are expanded
}

const { fetchWithAuth, API_BASE_URL } = useApi()
const { isAuthenticated } = useAuth()
const {
  preferredModel,
  availableModels: prefsAvailableModels,
  loadPreferences,
  setPreferredModel,
  getModelInfo
} = usePreferences()

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
const showSummary = ref(true); // Summary visible by default
const showFullTranscription = ref(false);

// Model selection state
const selectedModel = ref('gemma3:1b');
const availableModels = ref<ModelOption[]>(prefsAvailableModels);

// Configure marked options
marked.setOptions({
  breaks: true,        // Convert \n to <br>
  gfm: true,          // GitHub Flavored Markdown
});

// Load user preferences on component mount
onMounted(async () => {
  if (isAuthenticated.value) {
    await loadPreferences();
    selectedModel.value = preferredModel.value;
  }
});

// Helper functions
const renderMarkdown = (text: string): string => {
  try {
    return marked.parse(text) as string;
  } catch (error) {
    console.error('Error parsing markdown:', error);
    return text;
  }
};

const getModelDescription = (modelName: string): string => {
  const modelInfo = getModelInfo(modelName);
  return modelInfo?.description || 'General purpose model';
};

const onModelChange = async () => {
  console.log('Model changed to:', selectedModel.value);
  // Save the new preference to backend
  if (isAuthenticated.value) {
    const success = await setPreferredModel(selectedModel.value);
    if (success) {
      console.log('Model preference saved successfully');
    } else {
      console.error('Failed to save model preference');
    }
  }
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
      model: selectedModel.value,
      sources: data.sources || {},
      sourcesExpanded: false,
      expandedChunks: new Set()
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

const toggleSummary = () => {
  showSummary.value = !showSummary.value;
};

const toggleTranscription = () => {
  showFullTranscription.value = !showFullTranscription.value;
};

const reset = () => {
  hasTranscription.value = false;
  transcription.value = '';
  summary.value = '';
  messages.value = [];
  showSummary.value = true;
  showFullTranscription.value = false;
};

const scrollToBottom = async () => {
  await nextTick();
  const el = messagesContainer.value;
  if (el) el.scrollTop = el.scrollHeight;
};

// Toggle sources section expansion
const toggleSources = (message: Message) => {
  message.sourcesExpanded = !message.sourcesExpanded;
};

// Toggle individual chunk expansion
const toggleChunk = (message: Message, chunkNum: string) => {
  if (!message.expandedChunks) {
    message.expandedChunks = new Set();
  }

  if (message.expandedChunks.has(chunkNum)) {
    message.expandedChunks.delete(chunkNum);
  } else {
    message.expandedChunks.add(chunkNum);
  }
  // Force reactivity update
  message.expandedChunks = new Set(message.expandedChunks);
};

// Check if a chunk is expanded
const isChunkExpanded = (message: Message, chunkNum: string): boolean => {
  return message.expandedChunks?.has(chunkNum) || false;
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

/* Source Citations - Two-level collapsible */
.sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.sources-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
  user-select: none;
}

.sources-toggle:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.toggle-icon {
  font-size: 0.7rem;
  color: #666;
  width: 12px;
  display: inline-block;
}

.sources-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
  margin-left: 18px;
}

.source-item {
  display: flex;
  flex-direction: column;
}

.source-header {
  display: flex;
  align-items: baseline;
  gap: 6px;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
  user-select: none;
}

.source-header:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.chunk-toggle-icon {
  font-size: 0.65rem;
  color: #666;
  width: 10px;
  display: inline-block;
}

.source-number {
  font-weight: 600;
  color: #4A90E2;
  flex-shrink: 0;
  font-size: 0.8rem;
}

.source-title {
  color: #555;
  line-height: 1.4;
  font-size: 0.8rem;
}

.chunk-content {
  margin-top: 6px;
  margin-left: 26px;
  padding: 10px 12px;
  background-color: rgba(0, 0, 0, 0.03);
  border-left: 2px solid #4A90E2;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #444;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
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

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.transcription-summary h4 {
  margin: 0;
  color: #333;
}

.transcription-summary p {
  margin: 0 0 15px 0;
  color: #666;
  line-height: 1.6;
}

/* Summary markdown content styling */
.summary-content {
  margin: 0 0 15px 0;
  color: #666;
  line-height: 1.6;
}

.summary-content h2 {
  font-size: 1.1em;
  font-weight: 600;
  margin: 12px 0 8px 0;
  color: #333;
}

.summary-content h3 {
  font-size: 1em;
  font-weight: 600;
  margin: 10px 0 6px 0;
  color: #444;
}

.summary-content p {
  margin: 8px 0;
}

.summary-content ul,
.summary-content ol {
  margin: 8px 0;
  padding-left: 24px;
}

.summary-content li {
  margin: 4px 0;
}

.summary-content strong {
  font-weight: 600;
  color: #333;
}

.summary-content em {
  font-style: italic;
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

.toggle-btn-small {
  background-color: #6c757d;
  color: white;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
}

.toggle-btn-small:hover {
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

/* Markdown content styling */
.message-content {
  line-height: 1.6;
}

.message-content p {
  margin: 0 0 8px 0;
}

.message-content p:last-child {
  margin-bottom: 0;
}

.message-content strong {
  font-weight: 600;
}

.message-content em {
  font-style: italic;
}

.message-content ul,
.message-content ol {
  margin: 8px 0;
  padding-left: 24px;
}

.message-content li {
  margin: 4px 0;
}

.message-content code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.message-content pre {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-content pre code {
  background-color: transparent;
  padding: 0;
}

.message-content h1,
.message-content h2,
.message-content h3,
.message-content h4 {
  margin: 12px 0 8px 0;
  font-weight: 600;
}

.message-content h1 { font-size: 1.4em; }
.message-content h2 { font-size: 1.2em; }
.message-content h3 { font-size: 1.1em; }
.message-content h4 { font-size: 1em; }

/* Adjust code background for user messages */
.message-user .message-content code {
  background-color: rgba(255, 255, 255, 0.2);
}

.message-user .message-content pre {
  background-color: rgba(255, 255, 255, 0.2);
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