# Docker Container Publishing Guide

## Building the Container

### Local Build
```bash
docker build -t aimealplanner:latest .
```

### Build with Tag
```bash
docker build -t yourusername/aimealplanner:1.0.0 .
```

## Running the Container

### Basic Run
```bash
docker run -p 5000:5000 aimealplanner:latest
```

### Run with Environment Variables
```bash
docker run -p 5000:5000 \
  -e AI_BASE_URL=http://host.docker.internal:1234/v1 \
  -e AI_API_KEY=your-api-key \
  -e AI_MODEL=your-model \
  -e FLASK_DEBUG=false \
  aimealplanner:latest
```

### Run with Data Persistence
```bash
docker run -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e AI_BASE_URL=http://host.docker.internal:1234/v1 \
  aimealplanner:latest
```

### Run with Docker Compose
```bash
docker-compose up -d
```

## Publishing to Docker Hub

### 1. Login to Docker Hub
```bash
docker login
```

### 2. Tag the Image
```bash
docker tag aimealplanner:latest yourusername/aimealplanner:latest
docker tag aimealplanner:latest yourusername/aimealplanner:1.0.0
```

### 3. Push to Docker Hub
```bash
docker push yourusername/aimealplanner:latest
docker push yourusername/aimealplanner:1.0.0
```

## Publishing to GitHub Container Registry (ghcr.io)

### 1. Login to GitHub Container Registry
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### 2. Tag the Image
```bash
docker tag aimealplanner:latest ghcr.io/yourusername/aimealplanner:latest
docker tag aimealplanner:latest ghcr.io/yourusername/aimealplanner:1.0.0
```

### 3. Push to GitHub Container Registry
```bash
docker push ghcr.io/yourusername/aimealplanner:latest
docker push ghcr.io/yourusername/aimealplanner:1.0.0
```

## Environment Variables

The container supports the following environment variables at runtime:

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_BASE_URL` | Base URL for AI provider API | `http://localhost:1234/v1` |
| `AI_API_KEY` | API key for AI provider | `lm-studio` |
| `AI_MODEL` | Model name to use | `local-model` |
| `FLASK_DEBUG` | Enable Flask debug mode (development only) | `false` |

### Example: Running with Custom Variables
```bash
docker run -p 5000:5000 \
  -e AI_BASE_URL=http://192.168.1.100:8080/api/v1 \
  -e AI_API_KEY=my-secret-key \
  -e AI_MODEL=llama-2-7b \
  yourusername/aimealplanner:latest
```

## Health Check

The container includes a built-in health check that monitors the `/health` endpoint.

Check container health:
```bash
docker inspect --format='{{.State.Health.Status}}' <container-id>
```

## Security Best Practices

1. **Run as Non-Root**: The container runs as user `appuser` (UID 1000)
2. **No Debug Mode**: Always set `FLASK_DEBUG=false` in production
3. **Secret Management**: Use Docker secrets or environment files for sensitive data
4. **Network Security**: Use Docker networks to isolate containers

### Using Environment File
Create a `.env` file:
```env
AI_BASE_URL=http://host.docker.internal:1234/v1
AI_API_KEY=your-secret-key
AI_MODEL=your-model
FLASK_DEBUG=false
```

Run with env file:
```bash
docker run -p 5000:5000 --env-file .env aimealplanner:latest
```

## Multi-Architecture Builds

Build for multiple platforms (AMD64 and ARM64):

```bash
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t yourusername/aimealplanner:latest \
  --push .
```

## Automated Builds with GitHub Actions

The repository includes a GitHub Actions workflow that:
- Builds the Docker container on every PR
- Tests the container starts successfully
- Validates environment variable support
- Acts as a required PR gate

The workflow is triggered on:
- Pull requests to `main` branch
- Changes to Docker-related files

## Production Deployment

### Using Docker Compose (Recommended)
```yaml
version: '3.8'

services:
  aimealplanner:
    image: yourusername/aimealplanner:latest
    ports:
      - "5000:5000"
    environment:
      - AI_BASE_URL=${AI_BASE_URL}
      - AI_API_KEY=${AI_API_KEY}
      - AI_MODEL=${AI_MODEL}
    volumes:
      - meal-data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  meal-data:
```

### Using Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aimealplanner
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aimealplanner
  template:
    metadata:
      labels:
        app: aimealplanner
    spec:
      containers:
      - name: aimealplanner
        image: yourusername/aimealplanner:latest
        ports:
        - containerPort: 5000
        env:
        - name: AI_BASE_URL
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: base-url
        - name: AI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: api-key
        - name: AI_MODEL
          value: "your-model"
        volumeMounts:
        - name: data
          mountPath: /app/data
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 30
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: aimealplanner-data
```

## Monitoring

View container logs:
```bash
docker logs -f <container-id>
```

Monitor resource usage:
```bash
docker stats <container-id>
```

## Troubleshooting

### Container won't start
```bash
docker logs <container-id>
docker inspect <container-id>
```

### Health check failing
```bash
docker exec <container-id> curl http://localhost:5000/health
```

### Permission issues with data volume
```bash
# Fix permissions on host
sudo chown -R 1000:1000 ./data
```
