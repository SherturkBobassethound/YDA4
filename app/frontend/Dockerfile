# Build stage
FROM node:18-alpine as build-stage

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including dev dependencies needed for building)
RUN npm ci

# Copy source code
COPY . .

# Build arguments for API URLs and Supabase
ARG VITE_API_BASE_URL
ARG VITE_OLLAMA_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY

# Set environment variables for build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_OLLAMA_API_URL=${VITE_OLLAMA_API_URL}
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
ENV VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine as production-stage

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built files from build stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create a simple health check script
RUN echo '#!/bin/sh' > /health-check.sh && \
    echo 'curl -f http://localhost/health || exit 1' >> /health-check.sh && \
    chmod +x /health-check.sh

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /health-check.sh

# Start nginx
CMD ["nginx", "-g", "daemon off;"]