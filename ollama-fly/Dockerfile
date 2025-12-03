FROM ollama/ollama:latest

# Expose Ollama port
EXPOSE 11434

# Set environment variable to listen on all interfaces
ENV OLLAMA_HOST=0.0.0.0

# Start Ollama server
CMD ["/bin/ollama", "serve"]
