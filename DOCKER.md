# Docker Deployment Guide

## Architecture

**Modular & Plug-and-Play**: Works standalone or integrates with existing infrastructure.

```
┌─────────────────────────────────────────────────┐
│  Log Analyzer Toolkit (Dockerized)             │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┐         ┌──────────┐            │
│  │ Frontend │◄────────│ Backend  │            │
│  │ (Vue)    │         │ (FastAPI)│            │
│  │ :5173    │         │ :8000    │            │
│  └──────────┘         └────┬─────┘            │
│                            │                   │
│       Optional Connections │                   │
│       (via env vars)       │                   │
└────────────────────────────┼───────────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         │                                       │
    Your Existing                           Optional
    Infrastructure                          Services
         │                                       │
    ┌────┴────┐                         ┌───────┴────────┐
    │ Postgres│                         │  PostgreSQL    │
    │ Redis   │                         │  Redis         │
    │ S3      │                         │  MinIO         │
    │ Kafka   │                         │  RabbitMQ      │
    │ ES      │                         │  Elasticsearch │
    └─────────┘                         └────────────────┘
```

## Quick Start

### 1. Standalone (No Dependencies)

```bash
# Build and run
docker-compose up -d

# Access
open http://localhost:5173
```

### 2. With Optional Services

```bash
# Include PostgreSQL, Redis, MinIO, RabbitMQ, Elasticsearch
docker-compose -f docker-compose.yml -f docker-compose.services.yml up -d

# Verify all services
docker-compose ps
```

### 3. Connect to Existing Infrastructure

```bash
# Create .env file
cat > .env <<EOF
DATABASE_URL=postgresql://user:pass@your-db.example.com:5432/logs
REDIS_URL=redis://your-redis.example.com:6379/0
ELASTICSEARCH_URL=https://your-es.example.com:9200
EOF

# Run with your infrastructure
docker-compose up -d
```

## Real-Time Log Viewing

### WebSocket Live Tail

```javascript
// Connect to live log stream
const ws = new WebSocket('ws://localhost:8000/realtime/ws/logs/tail');

// Send file to tail
ws.send(JSON.stringify({
  file: '/app/uploads/application.log',
  lines: 50
}));

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New log:', data.line);
};
```

### Server-Sent Events for Errors

```html
<!DOCTYPE html>
<html>
<body>
  <div id="errors"></div>

  <script>
    const eventSource = new EventSource('http://localhost:8000/realtime/stream/errors');

    eventSource.onmessage = (event) => {
      const error = JSON.parse(event.data);
      document.getElementById('errors').innerHTML +=
        `<div style="color: red">${error.message}</div>`;
    };
  </script>
</body>
</html>
```

### REST API Tailing

```bash
# Tail logs via HTTP (SSE)
curl -N http://localhost:8000/realtime/tail/myapp.log?lines=100

# Stream continues indefinitely...
```

## Production Deployment

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml log-analyzer

# Scale backend
docker service scale log-analyzer_backend=3
```

### Kubernetes

```bash
# Build images
docker build -f Dockerfile.backend -t your-registry/log-analyzer-backend:v1 .
docker build -f Dockerfile.frontend -t your-registry/log-analyzer-frontend:v1 .

# Push to registry
docker push your-registry/log-analyzer-backend:v1
docker push your-registry/log-analyzer-frontend:v1

# Deploy
kubectl apply -f k8s/
```

### Cloud Platforms

#### AWS ECS

```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com
docker tag log-analyzer-backend:latest your-account.dkr.ecr.us-east-1.amazonaws.com/log-analyzer:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/log-analyzer:latest

# Deploy via ECS CLI or Console
```

#### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/your-project/log-analyzer
gcloud run deploy log-analyzer --image gcr.io/your-project/log-analyzer --platform managed
```

## Environment Variables

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHONUNBUFFERED` | 1 | Disable Python output buffering |
| `VITE_API_URL` | http://localhost:8000 | Backend API URL for frontend |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | sqlite:///./log_analyzer.db | Database connection string |

### Cache & Queue

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | None | Redis for caching and pubsub |
| `RABBITMQ_URL` | None | RabbitMQ for message queue |

### Object Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT` | None | S3-compatible storage endpoint |
| `MINIO_ACCESS_KEY` | None | Access key |
| `MINIO_SECRET_KEY` | None | Secret key |

### Search

| Variable | Default | Description |
|----------|---------|-------------|
| `ELASTICSEARCH_URL` | None | Elasticsearch cluster URL |

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Expected response
{"status":"healthy","version":"0.1.0","timestamp":"2026-02-10T12:00:00"}
```

### Logs

```bash
# View backend logs
docker-compose logs -f backend

# View all services
docker-compose logs -f

# Tail last 100 lines
docker-compose logs --tail=100 backend
```

### Metrics (Prometheus)

```bash
# Metrics endpoint
curl http://localhost:8000/metrics

# Example metrics:
# http_requests_total{method="GET",endpoint="/health",status="200"} 42
# log_files_analyzed_total 156
# log_errors_detected_total 89
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Port 8000 already in use
# 2. Database connection failed
# 3. Missing dependencies
```

### Can't connect to external services

```bash
# Test from container
docker-compose exec backend sh
curl -v postgres:5432  # Should connect
ping redis  # Should respond
```

### Permission issues with volumes

```bash
# Fix upload directory permissions
chmod 777 uploads/

# Or run with specific user
docker-compose run --user $(id -u):$(id -g) backend
```

## Security

### Production Checklist

- [ ] Change default passwords in docker-compose.services.yml
- [ ] Use secrets management (Docker Secrets, K8s Secrets)
- [ ] Enable TLS/HTTPS
- [ ] Set up authentication (JWT, OAuth)
- [ ] Configure CORS properly
- [ ] Use read-only root filesystem
- [ ] Run as non-root user
- [ ] Scan images for vulnerabilities
- [ ] Set resource limits

### Secure Configuration Example

```yaml
services:
  backend:
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    user: "1000:1000"
    environment:
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
    secrets:
      - jwt_secret

secrets:
  jwt_secret:
    external: true
```

## Development

### Hot Reload

```bash
# Mount source code for live updates
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Debug Mode

```bash
# Run with debugger port exposed
docker-compose run -p 5678:5678 backend python -m debugpy --listen 0.0.0.0:5678 -m uvicorn backend.main:app
```

## Backup & Restore

### Database Backup

```bash
# PostgreSQL
docker-compose exec postgres pg_dump -U loganalyzer log_analyzer > backup.sql

# Restore
cat backup.sql | docker-compose exec -T postgres psql -U loganalyzer log_analyzer
```

### Volume Backup

```bash
# Backup uploads
docker run --rm -v log-analyzer-toolkit_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads-backup.tar.gz /data

# Restore
docker run --rm -v log-analyzer-toolkit_uploads:/data -v $(pwd):/backup alpine tar xzf /backup/uploads-backup.tar.gz -C /
```
