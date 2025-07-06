# Frontend Docker Setup

This directory contains Docker configuration for the Vue.js frontend application using nginx for production deployment.

## Files Overview

- `Dockerfile` - Production build with Node.js + nginx multi-stage build
- `nginx.conf` - nginx configuration for serving the Vue app
- `.dockerignore` - Files to exclude from Docker build

## Quick Start

### Build and Run Production Container

```bash
# Build the Docker image
docker build -t frontend-app .

# Run the container
docker run -p 80:80 frontend-app

# Access the app at http://localhost
```

## Docker Commands

### Build the Image
```bash
# Build with a specific tag
docker build -t frontend-app:latest .

# Build with a specific version
docker build -t frontend-app:v1.0.0 .
```

### Run the Container
```bash
# Run on port 80
docker run -p 80:80 frontend-app

# Run on a different port
docker run -p 3000:80 frontend-app

# Run in detached mode
docker run -d -p 80:80 frontend-app

# Run with a specific name
docker run -d -p 80:80 --name my-frontend frontend-app
```

### Container Management
```bash
# Stop the container
docker stop my-frontend

# Remove the container
docker rm my-frontend

# View container logs
docker logs my-frontend

# Execute commands in the container
docker exec -it my-frontend sh
```

## How It Works

The setup uses a **multi-stage build** approach:

1. **Build Stage**: Uses Node.js Alpine to install dependencies and build the Vue app
2. **Production Stage**: Uses nginx Alpine to serve the built static files

### Build Process
1. Copy `package.json` and install dependencies
2. Copy source code and build with `npm run build`
3. Copy built files from `dist/` to nginx's `/usr/share/nginx/html/`
4. Serve with optimized nginx configuration

## nginx Configuration Features

The `nginx.conf` includes:

- ✅ **SPA Routing Support**: Handles Vue Router with `try_files $uri $uri/ /index.html`
- ✅ **Static Asset Optimization**: Long-term caching for JS/CSS files
- ✅ **Gzip Compression**: Reduces file sizes for faster loading
- ✅ **Security Headers**: XSS protection, content type sniffing prevention
- ✅ **Health Check Endpoint**: `/health` for monitoring
- ✅ **Error Handling**: Proper 404/500 error pages

## Development

For development, continue using the standard Vite dev server:

```bash
npm run dev
# or
yarn dev
```

No Docker container is needed for development - this keeps the development experience fast and simple.

## Benefits of This Approach

1. **Production Optimized**: nginx is battle-tested for serving static files
2. **Small Image Size**: Alpine-based images are lightweight
3. **Fast Loading**: Gzip compression and caching optimizations
4. **Security**: Proper security headers and configurations
5. **Simple Development**: No container overhead during development

## Notes

- The production container runs on port 80 (standard HTTP port)
- Static assets are cached for 1 year with immutable cache headers
- All routes fall back to `index.html` for SPA routing support
- nginx handles all the complexity of serving static files efficiently 