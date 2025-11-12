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

    <div class="divider">OR</div>

    <!-- File Upload Section -->
    <div class="file-upload-section">
      <h3>Upload Audio File</h3>
      <div class="file-upload">
        <input
          type="file"
          ref="fileInput"
          @change="handleFileSelect"
          accept="audio/*"
          class="file-input"
        />
        <button @click="triggerFileSelect" class="upload-btn">
          Choose Audio File
        </button>
        <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
        <button 
          v-if="selectedFile" 
          @click="processAudio" 
          :disabled="isProcessing"
          class="process-btn"
        >
          {{ isProcessing ? 'Processing...' : 'Process Audio' }}
        </button>
      </div>
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
import { ref, onMounted } from 'vue'

// Get API base URLs from environment or use container-aware defaults
const getApiBaseUrl = (): string => {
  // Check if running in browser (client-side)
  if (typeof window !== 'undefined') {
    // If hostname is localhost, we're in development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8000';
    }
    // Otherwise, use the current host (for production containers)
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  // Fallback for SSR
  return 'http://backend:8000';
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getApiBaseUrl();

// Universal URL processing state
const universalUrl = ref('');
const detectedUrlType = ref('');
const isProcessing = ref(false);
const processingStatus = ref('');

// File upload state
const selectedFile = ref<File | null>(null);
const fileInput = ref<HTMLInputElement>();

// API status tracking
const apiStatus = ref({
  backend: false,
  ollama: false
});

// Check API status on mount
onMounted(async () => {
  await checkApiStatus();
  // Check status every 30 seconds
  setInterval(checkApiStatus, 30000);
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

// Process Apple Podcasts URL (placeholder for future implementation)
const processPodcastUrl = async (url: string) => {
  processingStatus.value = 'Apple Podcasts processing is not yet implemented. Coming soon!';
  console.log('Processing Apple Podcast URL:', url);

  // TODO: Implement Apple Podcasts processing
  // This would call a backend endpoint similar to /process-youtube
  // For now, just show a message

  setTimeout(() => {
    processingStatus.value = '';
  }, 3000);
};

// File handling methods
const triggerFileSelect = () => {
  fileInput.value?.click();
};

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0];
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
    const response = await fetch(`${API_BASE_URL}/process-youtube`, {
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
    handleTranscriptionResult(data);
    
  } catch (error: any) {
    clearInterval(progressInterval);
    processingStatus.value = handleApiError(error, 'YouTube processing');
  } finally {
    isProcessing.value = false;
  }
};

const processAudio = async () => {
  if (!selectedFile.value) return;
  
  if (!apiStatus.value.backend) {
    processingStatus.value = 'Backend API is not available. Please wait for services to start.';
    return;
  }
  
  isProcessing.value = true;
  processingStatus.value = 'Starting audio processing...';
  
  // Create progress simulation for audio processing
  const progressSteps = [
    'Uploading audio file...',
    'Transcribing with Whisper (this may take several minutes)...',
    'Generating summary with Ollama...',
    'Finalizing...'
  ];
  
  let stepIndex = 0;
  const progressInterval = setInterval(() => {
    if (stepIndex < progressSteps.length - 1) {
      processingStatus.value = progressSteps[stepIndex];
      stepIndex++;
    }
  }, 10000); // Update every 10 seconds
  
  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);
    
    const response = await fetch(`${API_BASE_URL}/process-audio`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(600000) // 10 minute timeout
    });
    
    clearInterval(progressInterval);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || 'Failed to process audio file');
    }
    
    const data = await response.json();
    handleTranscriptionResult(data);
    
  } catch (error: any) {
    clearInterval(progressInterval);
    processingStatus.value = handleApiError(error, 'Audio processing');
  } finally {
    isProcessing.value = false;
  }
};

const handleTranscriptionResult = (data: any) => {
  processingStatus.value = 'Processing complete!';

  // Emit event to parent component (ChatApp) with the transcription data
  emit('transcription-complete', {
    transcription: data.transcription,
    summary: data.summary
  });

  // Clear the form
  universalUrl.value = '';
  detectedUrlType.value = '';
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = '';
  }

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

/* Podcast List Styles */
.sidebar ul {
  list-style: none;
  padding: 0;
  margin: 0 0 15px 0;
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

.add-source {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-input {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
  outline: none;
}

.source-input:focus {
  border-color: #1976d2;
}

.add-btn {
  padding: 10px;
  background-color: #1976d2;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.add-btn:hover {
  background-color: #1565c0;
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