FROM ollama/ollama:latest

# Expose Ollama port
EXPOSE 11434

# Set environment variable to listen on all interfaces
ENV OLLAMA_HOST=0.0.0.0

# Create a startup script that will be our ENTRYPOINT
RUN echo '#!/bin/sh' > /start.sh && \
    echo 'exec /bin/ollama serve' >> /start.sh && \
    chmod +x /start.sh

# Set the script as ENTRYPOINT to completely override base image
ENTRYPOINT ["/start.sh"]
