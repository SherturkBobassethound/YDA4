<template>
  <div class="sidebar">
    <h2>Podcasts</h2>
    
    <!-- Universal URL Processing Section -->
    <div class="processing-section">
      <h3>Process URL</h3>
      <div class="input-group">
        <input
          type="text"
          v-model="universalUrl"
          placeholder="Paste YouTube or Apple Podcasts URL..."
          class="url-input"
          @input="detectUrlType"
        />
        <div v-if="detectedUrlType" class="url-type-indicator">
          {{ detectedUrlType }}
        </div>
        <button @click="processUrl" :disabled="isProcessing || !universalUrl.trim()" class="process-btn">
          {{ isProcessing ? 'Processing...' : 'Process' }}
        </button>
      </div>
      <div v-if="processingStatus" class="status">{{ processingStatus }}</div>
    </div>

    <!-- Sources List -->
    <div v-if="isAuthenticated" class="sources-section">
      <h3>Your Sources</h3>
      <ul v-if="sources.length > 0" class="sources-list">
        <li v-for="(source, index) in sources" :key="index" class="source-item">
          <span class="source-text" :title="source.title">{{ source.title }}</span>
          <button @click="confirmDelete(index)" class="remove-btn">×</button>
        </li>
      </ul>
      <p v-else class="no-sources">No sources added yet</p>
    </div>

    <!-- API Status Indicator -->
    <div class="api-status">
      <h4>Service Status</h4>
      <div class="status-indicators">
        <div class="status-item">
          <span class="status-dot" :class="{ 'online': apiStatus.backend, 'offline': !apiStatus.backend }"></span>
          Backend API
        </div>
        <div class="status-item">
          <span class="status-dot" :class="{ 'online': apiStatus.ollama, 'offline': !apiStatus.ollama }"></span>
          Ollama API
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useApi } from '../composables/useApi'
import { useAuth } from '../composables/useAuth'

const { fetchWithAuth, API_BASE_URL } = useApi()
const { isAuthenticated } = useAuth()

// Universal URL processing state
const universalUrl = ref('');
const detectedUrlType = ref('');
const isProcessing = ref(false);
const processingStatus = ref('');

// Sources state
interface Source {
  id: string;
  title: string;
  url: string;
  type: 'youtube' | 'podcast';
  addedAt: string;
}

const sources = ref<Source[]>([]);
const showDeleteModal = ref(false);
const sourceToDelete = ref<number | null>(null);

// API status tracking
const apiStatus = ref({
  backend: false,
  ollama: false
});

// Check API status on mount and load sources
onMounted(async () => {
  await checkApiStatus();
  // Check status every 30 seconds
  setInterval(checkApiStatus, 30000);

  // Load user's sources if authenticated
  if (isAuthenticated.value) {
    await loadSources();
  }
});

// Watch for authentication changes and load sources when user logs in
watch(isAuthenticated, async (newValue, oldValue) => {
  if (newValue && !oldValue) {
    // User just logged in
    await loadSources();
  } else if (!newValue && oldValue) {
    // User just logged out
    sources.value = [];
  }
});

const checkApiStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      signal: AbortSignal.timeout(5000)
    });
    if (response.ok) {
      const data = await response.json();
      apiStatus.value.backend = data.status === 'healthy';
      apiStatus.value.ollama = data.ollama_api === 'connected';
    } else {
      apiStatus.value.backend = false;
      apiStatus.value.ollama = false;
    }
  } catch (error) {
    console.warn('API status check failed:', error);
    apiStatus.value.backend = false;
    apiStatus.value.ollama = false;
  }
};

// URL detection logic
const detectUrlType = () => {
  const url = universalUrl.value.trim().toLowerCase();

  if (!url) {
    detectedUrlType.value = '';
    return;
  }

  // Check for YouTube URLs
  if (url.includes('youtube.com') || url.includes('youtu.be')) {
    detectedUrlType.value = '🎥 YouTube Video';
    return;
  }

  // Check for Apple Podcasts URLs
  if (url.includes('podcasts.apple.com') || url.includes('itunes.apple.com')) {
    detectedUrlType.value = '🎙️ Apple Podcast';
    return;
  }

  // Unknown URL type
  detectedUrlType.value = '❓ Unknown URL type';
};

// Universal URL processing router
const processUrl = async () => {
  const url = universalUrl.value.trim();
  if (!url) return;

  detectUrlType();

  // Route based on detected URL type
  if (detectedUrlType.value.includes('YouTube')) {
    await processYoutubeUrl(url);
  } else if (detectedUrlType.value.includes('Podcast')) {
    await processPodcastUrl(url);
  } else {
    processingStatus.value = 'Unsupported URL type. Please use YouTube or Apple Podcasts URLs.';
    setTimeout(() => {
      processingStatus.value = '';
    }, 3000);
  }
};

// Process Apple Podcasts URL
const processPodcastUrl = async (url: string) => {
  if (!url) return;

  if (!isAuthenticated.value) {
    processingStatus.value = 'Please log in to process content.';
    return;
  }

  if (!apiStatus.value.backend) {
    processingStatus.value = 'Backend API is not available. Please wait for services to start.';
    return;
  }

  isProcessing.value = true;
  processingStatus.value = 'Starting Apple Podcast processing...';

  // Create progress simulation
  const progressSteps = [
    'Fetching podcast metadata...',
    'Attempting to scrape transcript...',
    'Downloading podcast audio (if needed)...',
    'Transcribing with Whisper (this may take several minutes)...',
    'Generating summary with Ollama...',
    'Almost done...'
  ];

  let stepIndex = 0;
  const progressInterval = setInterval(() => {
    if (stepIndex < progressSteps.length - 1) {
      processingStatus.value = progressSteps[stepIndex];
      stepIndex++;
    }
  }, 15000); // Update every 15 seconds

  try {
    const response = await fetchWithAuth(`${API_BASE_URL}/process-url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: url
      }),
      signal: AbortSignal.timeout(600000) // 10 minute timeout
    });

    clearInterval(progressInterval);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || 'Failed to process Apple Podcast URL');
    }

    const data = await response.json();
    handleTranscriptionResult(data, url);

  } catch (error: any) {
    clearInterval(progressInterval);
    processingStatus.value = handleApiError(error, 'Apple Podcast processing');
  } finally {
    isProcessing.value = false;
  }
};

// Source management methods
const loadSources = async () => {
  try {
    const response = await fetchWithAuth(`${API_BASE_URL}/sources`);

    if (!response.ok) {
      throw new Error(`Failed to load sources: ${response.statusText}`);
    }

    const data = await response.json();
    sources.value = data.sources || [];
    console.log('Sources loaded:', sources.value.length);
  } catch (error) {
    console.error('Failed to load sources:', error);
    // Don't show an alert on load failure - just log it
  }
};

const confirmDelete = (index: number) => {
  const source = sources.value[index];
  const confirmed = window.confirm(
    `Are you sure you want to delete "${source.title}"?\n\nThis will permanently remove the transcription from your vector database.`
  );

  if (confirmed) {
    deleteSource(index);
  }
};

const deleteSource = async (index: number) => {
  const source = sources.value[index];

  try {
    const response = await fetchWithAuth(`${API_BASE_URL}/sources/${source.id}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error(`Failed to delete source: ${response.statusText}`);
    }

    // Remove from local array only after successful backend deletion
    sources.value.splice(index, 1);
    console.log('Source deleted:', source.title);
  } catch (error) {
    console.error('Failed to delete source:', error);
    alert('Failed to delete source. Please try again.');
  }
};

// Enhanced error handling with user-friendly messages
const handleApiError = (error: any, context: string): string => {
  console.error(`${context} error:`, error);
  
  if (error.name === 'TimeoutError') {
    return `${context} is taking longer than expected. This might be a very long file. Please try a shorter clip or try again later.`;
  }
  
  if (error.message?.includes('fetch')) {
    return `Cannot connect to the backend service. Please check that all services are running.`;
  }
  
  if (error.message?.includes('503')) {
    return `Backend services are temporarily unavailable. Please wait a moment and try again.`;
  }
  
  return `${context} failed: ${error.message || 'Unknown error'}. Please try again.`;
};

// API processing methods with improved error handling
const processYoutubeUrl = async (url: string) => {
  if (!url) return;

  if (!isAuthenticated.value) {
    processingStatus.value = 'Please log in to process content.';
    return;
  }

  if (!apiStatus.value.backend) {
    processingStatus.value = 'Backend API is not available. Please wait for services to start.';
    return;
  }

  isProcessing.value = true;
  processingStatus.value = 'Starting YouTube processing...';

  // Create progress simulation
  const progressSteps = [
    'Downloading YouTube video...',
    'Extracting audio...',
    'Transcribing with Whisper (this may take several minutes)...',
    'Generating summary with Ollama...',
    'Almost done...'
  ];

  let stepIndex = 0;
  const progressInterval = setInterval(() => {
    if (stepIndex < progressSteps.length - 1) {
      processingStatus.value = progressSteps[stepIndex];
      stepIndex++;
    }
  }, 15000); // Update every 15 seconds

  try {
    const response = await fetchWithAuth(`${API_BASE_URL}/process-youtube`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        youtube_url: url
      }),
      signal: AbortSignal.timeout(600000) // 10 minute timeout
    });

    clearInterval(progressInterval);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || 'Failed to process YouTube URL');
    }

    const data = await response.json();
    handleTranscriptionResult(data, url);

  } catch (error: any) {
    clearInterval(progressInterval);
    processingStatus.value = handleApiError(error, 'YouTube processing');
  } finally {
    isProcessing.value = false;
  }
};

const handleTranscriptionResult = async (data: any, sourceUrl: string = '') => {
  processingStatus.value = 'Processing complete!';

  // Reload sources from backend to get the saved source with correct ID
  // The backend automatically saves sources when processing completes
  if (sourceUrl && isAuthenticated.value) {
    await loadSources();
  }

  // Emit event to parent component (ChatApp) with the transcription data
  emit('transcription-complete', {
    transcription: data.transcription,
    summary: data.summary
  });

  // Clear the form
  universalUrl.value = '';
  detectedUrlType.value = '';

  // Clear status after a delay
  setTimeout(() => {
    processingStatus.value = '';
  }, 3000);
};

// Define emit for communication with parent
const emit = defineEmits<{
  'transcription-complete': [data: { transcription: string; summary: string }]
}>();
</script>

<style scoped>
.sidebar {
  width: 300px;
  flex-shrink: 0;
  padding: 20px;
  background-color: #f8f9fa;
  border-right: 1px solid #e0e0e0;
  height: 100vh;
  overflow-y: auto;
}

.sidebar h2 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 600;
}

.sidebar h3 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 1.1rem;
  font-weight: 500;
}

.sidebar h4 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 1rem;
  font-weight: 500;
}

/* Processing Section Styles */
.processing-section,
.file-upload-section,
.podcast-list-section {
  margin-bottom: 25px;
}

.input-group {
  margin-bottom: 15px;
}

.url-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  margin-bottom: 10px;
  font-size: 0.9rem;
  outline: none;
}

.url-input:focus {
  border-color: #1976d2;
}

.url-type-indicator {
  padding: 8px 12px;
  margin-bottom: 10px;
  background-color: #e3f2fd;
  border: 1px solid #90caf9;
  border-radius: 6px;
  font-size: 0.85rem;
  color: #1565c0;
  text-align: center;
  font-weight: 500;
}

.process-btn {
  width: 100%;
  padding: 10px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.9rem;
}

.process-btn:hover:not(:disabled) {
  background-color: #218838;
}

.process-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.status {
  margin-top: 10px;
  padding: 8px;
  background-color: #e9ecef;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #495057;
  text-align: center;
}

/* File Upload Styles */
.file-upload {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}

.file-input {
  display: none;
}

.upload-btn {
  width: 100%;
  padding: 10px;
  background-color: #17a2b8;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.9rem;
}

.upload-btn:hover {
  background-color: #138496;
}

.file-name {
  font-size: 0.8rem;
  color: #666;
  text-align: center;
  word-break: break-all;
}

/* Divider */
.divider {
  margin: 20px 0;
  color: #666;
  font-weight: 500;
  text-align: center;
  font-size: 0.9rem;
}

/* Sources Section Styles */
.sources-section {
  margin-bottom: 25px;
}

.sources-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.no-sources {
  text-align: center;
  color: #999;
  font-size: 0.9rem;
  padding: 20px;
  font-style: italic;
}

.source-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.source-text {
  flex: 1;
  color: #333;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}

.remove-btn {
  background-color: #ff4757;
  border: none;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.remove-btn:hover {
  background-color: #ff3742;
}

/* API Status Styles */
.api-status {
  margin-top: 25px;
  padding: 15px;
  background-color: #ffffff;
  border: 1px solid #dee2e6;
  border-radius: 8px;
}

.status-indicators {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: #666;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.online {
  background-color: #28a745;
}

.status-dot.offline {
  background-color: #dc3545;
}
</style>