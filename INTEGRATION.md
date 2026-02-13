# Integration Guide

## Quick Start - Standalone

```bash
# Just the app (uses SQLite, no dependencies)
docker-compose up -d

# Access:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

## Plug-and-Play with Existing Infrastructure

### Connect to Existing Database

```bash
# .env file
DATABASE_URL=postgresql://user:pass@your-postgres.example.com:5432/logs

docker-compose up -d
```

### Connect to Existing Redis

```bash
export REDIS_URL=redis://your-redis.example.com:6379/0
docker-compose up -d
```

### Connect to Existing Elasticsearch

```bash
export ELASTICSEARCH_URL=https://your-es-cluster.example.com:9200
docker-compose up -d
```

### Use All Optional Services

```bash
# Includes PostgreSQL, Redis, MinIO, RabbitMQ, Elasticsearch
docker-compose -f docker-compose.yml -f docker-compose.services.yml up -d
```

## Real-Time Log Streaming

### WebSocket Endpoint

```javascript
// Connect to live log stream
const ws = new WebSocket('ws://localhost:8000/ws/logs/tail');

ws.onmessage = (event) => {
  const logEntry = JSON.parse(event.data);
  console.log('New log:', logEntry);
};
```

### Server-Sent Events (SSE)

```javascript
// Stream errors in real-time
const eventSource = new EventSource('http://localhost:8000/api/stream/errors');

eventSource.onmessage = (event) => {
  const error = JSON.parse(event.data);
  console.error('New error:', error);
};
```

### REST API Polling

```bash
# Get recent errors (last 5 minutes)
curl http://localhost:8000/api/logs/errors?since=5m

# Tail log file
curl http://localhost:8000/api/logs/tail/your-file.log?lines=100
```

## Kubernetes Integration

### Deploy to Existing K8s Cluster

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: log-analyzer
spec:
  replicas: 2
  selector:
    matchLabels:
      app: log-analyzer
  template:
    metadata:
      labels:
        app: log-analyzer
    spec:
      containers:
      - name: backend
        image: log-analyzer-toolkit-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: log-analyzer-secrets
              key: database-url
        - name: REDIS_URL
          value: redis://redis-service:6379
```

### Collect Logs from K8s Pods

```bash
# Stream logs from specific pod
kubectl logs -f pod-name | \
  curl -X POST http://localhost:8000/api/logs/stream \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @-
```

## API Integration Patterns

### Push Logs via API

```python
import requests

# Single log entry
requests.post('http://localhost:8000/api/logs/ingest', json={
    'timestamp': '2026-02-10T12:00:00Z',
    'level': 'ERROR',
    'message': 'Database connection failed',
    'source': 'api-service'
})

# Batch upload
with open('app.log', 'rb') as f:
    requests.post('http://localhost:8000/api/logs/upload',
                  files={'file': f})
```

### Query Analyzed Logs

```python
# Get analysis results
response = requests.get('http://localhost:8000/api/analysis/latest')
analysis = response.json()

print(f"Total errors: {analysis['error_count']}")
print(f"Top error: {analysis['top_errors'][0]}")
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | SQLite | PostgreSQL/MySQL connection string |
| `REDIS_URL` | None | Redis for caching and real-time |
| `ELASTICSEARCH_URL` | None | For full-text log search |
| `MINIO_ENDPOINT` | None | S3-compatible object storage |
| `RABBITMQ_URL` | None | Message queue for log streaming |
| `LOG_RETENTION_DAYS` | 30 | Auto-delete logs older than N days |
| `MAX_UPLOAD_SIZE_MB` | 100 | Maximum log file size |
| `ENABLE_REALTIME` | true | Enable WebSocket streaming |

## Monitoring Integration

### Prometheus Metrics

```bash
# Metrics endpoint
curl http://localhost:8000/metrics
```

### Grafana Dashboard

Import dashboard: `grafana-dashboard.json` (in `/docs` folder)

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: log-analyzer
    rules:
      - alert: HighErrorRate
        expr: log_errors_total > 100
        for: 5m
        annotations:
          summary: "High error rate detected"
```

## Security Best Practices

1. **Use Secrets Management**
   ```bash
   # Docker Swarm
   docker secret create db_password password.txt

   # Kubernetes
   kubectl create secret generic log-analyzer-secrets \
     --from-literal=database-url="postgresql://..."
   ```

2. **Enable Authentication**
   ```bash
   export AUTH_ENABLED=true
   export JWT_SECRET="your-secret-key"
   ```

3. **Use TLS**
   ```bash
   # Mount certificates
   docker-compose up -d \
     -v /path/to/certs:/app/certs
   ```

## Troubleshooting

### Check Service Health

```bash
# All services
docker-compose ps

# Backend health
curl http://localhost:8000/health

# View logs
docker-compose logs -f backend
```

### Connection Test Script

```python
# test_connections.py
import os
import sys

def test_postgres():
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        print("✓ PostgreSQL connected")
    except Exception as e:
        print(f"✗ PostgreSQL failed: {e}")

def test_redis():
    try:
        import redis
        r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        r.ping()
        print("✓ Redis connected")
    except Exception as e:
        print(f"✗ Redis failed: {e}")

if __name__ == '__main__':
    test_postgres()
    test_redis()
```
