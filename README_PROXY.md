# OpenAI-Compatible Proxy Server

A production-ready OpenAI-compatible proxy server built with FastAPI that supports multiple LLM providers, intelligent fallback, secure key management, and comprehensive monitoring.

## Features

### Core Functionality
- **OpenAI API Compatibility**: Drop-in replacement for OpenAI API endpoints
- **Multi-Provider Support**: OpenAI, Anthropic, Ollama, and custom providers
- **Intelligent Fallback**: Automatic failover with circuit breaker pattern
- **Secure Key Management**: Encrypted API key storage with rotation support
- **Rate Limiting**: Redis-based rate limiting per key, tenant, and IP
- **Model Mapping**: Flexible mapping from client model names to provider models

### Security & Monitoring
- **Encrypted Storage**: API keys encrypted at rest using Fernet encryption
- **Structured Logging**: JSON logs with request tracing and audit trails
- **Prometheus Metrics**: Request latency, error rates, fallback counts
- **Health Endpoints**: Ready/live checks for Kubernetes deployments
- **Admin API**: Secure management interface for providers, keys, and mappings

### Production Features
- **Circuit Breaker**: Automatic provider health monitoring and recovery
- **Request Auditing**: Comprehensive audit logs with optional content storage
- **S3 Integration**: Store large request/response payloads in object storage
- **Database Migrations**: Alembic-based schema management
- **Docker Support**: Ready-to-deploy containers with docker-compose

## Quick Start

### 1. Environment Setup

```bash
# Clone and install dependencies
git clone <repository>
cd template-python
pip install -e .

# Copy environment configuration
cp .env.proxy .env
```

### 2. Infrastructure Setup

Start required services with Docker Compose:

```bash
docker-compose up -d postgres redis minio
```

### 3. Database Setup

Initialize the database and create sample data:

```bash
python setup_db.py
```

### 4. Start the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

### 5. Test the API

```bash
# List available models
curl -H "Authorization: Bearer mock-api-key-123" \
     http://localhost:8000/v1/models

# Chat completion
curl -H "Authorization: Bearer mock-api-key-123" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [{"role": "user", "content": "Hello!"}]
     }' \
     http://localhost:8000/v1/chat/completions

# Streaming chat completion
curl -H "Authorization: Bearer mock-api-key-123" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [{"role": "user", "content": "Hello!"}],
       "stream": true
     }' \
     http://localhost:8000/v1/chat/completions
```

## API Endpoints

### OpenAI-Compatible Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/chat/completions` | Chat completions (GPT-3.5, GPT-4) |
| `POST /v1/completions` | Text completions |
| `POST /v1/embeddings` | Text embeddings |
| `GET /v1/models` | List available models |

### Admin Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /admin/providers` | List providers |
| `POST /admin/providers` | Create provider |
| `GET /admin/keys` | List API keys |
| `POST /admin/keys` | Add API key |
| `GET /admin/mappings` | List model mappings |
| `POST /admin/mappings` | Create model mapping |
| `GET /admin/health` | System health status |

### Monitoring Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /readyz` | Readiness check |
| `GET /metrics` | Prometheus metrics |

## Configuration

### Environment Variables

```bash
# Application
APP_NAME=OpenAI Proxy
APP_PORT=8000
APP_DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/openai_proxy

# Redis
REDIS_URL=redis://localhost:6379/0

# S3 Storage
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-32-char-encryption-key-here

# Rate Limiting
RATE_LIMIT_GLOBAL_RPM=1000
RATE_LIMIT_PER_KEY_RPM=100
RATE_LIMIT_PER_IP_RPM=60
```

### Provider Configuration

```json
{
  "name": "openai-primary",
  "provider_type": "openai",
  "base_url": "https://api.openai.com/v1",
  "config": {
    "timeout": 30,
    "max_retries": 3
  }
}
```

### Model Mapping Example

```json
{
  "alias_name": "gpt-4",
  "provider_id": 1,
  "provider_model_name": "gpt-4-0613",
  "order_index": 0,
  "is_default": true,
  "config": {
    "temperature": 0.7,
    "max_tokens": 4000
  }
}
```

## Architecture

### Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Rate Limiter   │    │  Key Manager    │
│                 │    │     (Redis)      │    │   (Database)    │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • Authentication│    │ • Per-key limits │    │ • Key selection │
│ • Request ID    │    │ • IP-based limits│    │ • Health tracking│
│ • Logging       │    │ • Global limits  │    │ • Encryption    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Fallback Engine │
                    │                 │
                    │ • Circuit Breaker│
                    │ • Retry Logic   │
                    │ • Provider Health│
                    └─────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
  ┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
  │ OpenAI        │    │ Anthropic       │    │ Custom Provider │
  │ Provider      │    │ Provider        │    │ (Mock/Ollama)   │
  └───────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **Request Ingestion**: FastAPI receives request with authentication
2. **Rate Limiting**: Redis-based checks for limits compliance
3. **Model Resolution**: Map client model name to provider/model
4. **Key Selection**: Choose healthy API key using selection strategy
5. **Provider Execution**: Forward request to selected provider
6. **Fallback Handling**: Retry with different keys/providers on failure
7. **Response Processing**: Convert provider response to OpenAI format
8. **Audit Logging**: Record request details and metrics

## Deployment

### Docker

```bash
# Build image
docker build -t openai-proxy .

# Run with docker-compose
docker-compose up -d
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openai-proxy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: openai-proxy
  template:
    metadata:
      labels:
        app: openai-proxy
    spec:
      containers:
      - name: proxy
        image: openai-proxy:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: proxy-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: proxy-secrets
              key: redis-url
```

## Monitoring

### Metrics

The proxy exposes Prometheus metrics at `/metrics`:

- `proxy_requests_total`: Total requests by method, endpoint, status
- `proxy_request_duration_seconds`: Request duration histogram
- `proxy_provider_requests_total`: Provider requests by provider, model, status
- `proxy_fallbacks_total`: Fallback attempts by model and reason

### Grafana Dashboard

Import the included Grafana dashboard (`grafana/dashboard.json`) for monitoring:

- Request rate and latency
- Error rates by provider
- Fallback frequency
- Key health status
- Rate limiting metrics

### Alerting

Example Prometheus alerts:

```yaml
groups:
- name: openai-proxy
  rules:
  - alert: HighErrorRate
    expr: rate(proxy_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    annotations:
      summary: High error rate detected
      
  - alert: ProviderDown
    expr: proxy_provider_requests_total{status="error"} > 0
    for: 1m
    annotations:
      summary: Provider experiencing errors
```

## Security

### API Key Management

- Keys are encrypted at rest using Fernet symmetric encryption
- Master encryption key should be managed via external key management (Vault, AWS KMS)
- Keys are masked in logs (only last 4 characters visible)
- Automatic key rotation support via admin API

### Access Control

- Bearer token authentication for all API endpoints
- Admin endpoints require special admin API keys
- Rate limiting prevents abuse
- Request auditing for compliance

### Best Practices

1. **Rotate Encryption Keys**: Regularly rotate master encryption key
2. **Monitor Usage**: Set up alerting for unusual patterns
3. **Limit Permissions**: Use least-privilege API keys
4. **Secure Storage**: Store secrets in external key management system
5. **Network Security**: Use TLS for all communications

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/proxy/

# Run with coverage
pytest --cov=src/proxy
```

### Adding New Providers

1. Create provider class inheriting from `BaseProvider`
2. Implement required methods: `chat_completion`, `embedding`, `list_models`
3. Add provider type to `ProviderType` enum
4. Register in provider factory function
5. Add configuration schema if needed

### Custom Middleware

Add custom middleware to the FastAPI app:

```python
from starlette.middleware.base import BaseHTTPMiddleware

class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Custom logic here
        response = await call_next(request)
        return response

app.add_middleware(CustomMiddleware)
```

## Troubleshooting

### Common Issues

1. **Database Connection**: Check PostgreSQL connectivity and credentials
2. **Redis Connection**: Verify Redis is running and accessible
3. **Provider Errors**: Check API keys and provider base URLs
4. **Rate Limiting**: Verify Redis time synchronization
5. **Circuit Breaker**: Check provider health and failure thresholds

### Debug Mode

Enable debug mode for detailed logging:

```bash
export APP_DEBUG=true
export LOG_LEVEL=DEBUG
python main.py
```

### Health Checks

Check system health:

```bash
# Basic health
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/readyz

# Detailed system status
curl -H "Authorization: Bearer admin-key" \
     http://localhost:8000/admin/health
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request with description

For support, please open an issue on GitHub.