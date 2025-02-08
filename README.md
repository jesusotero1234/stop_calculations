# Tour Generator

A service that generates themed tour stops using local Llama model (phi4) and OpenStreetMap validation.

## Prerequisites

1. Install Ollama and run the phi4 model:
```bash
# Install Ollama
brew install ollama

# Run phi4 model
ollama run phi4:latest
```

## Setup and Testing

1. Verify Llama connection:
```bash
# Install dependencies
pip install aiohttp

# Run test script to verify Llama connection
python test_llama.py

# This will test connectivity and find the best host configuration
```

2. Create `.env` file with the correct host:
```bash
# API Configuration
API_TITLE="Tour Generator"
API_VERSION="2.0.0"

# Llama Configuration
LLAMA_HOST=host.docker.internal  # Use result from test script
LLAMA_PORT=11434

# Service Configuration
MIN_STOPS=2
MAX_STOPS=15
MIN_DURATION=30
MAX_DURATION=240
```

3. Start the service:
```bash
# Build and start containers
docker compose up --build
```

4. Test the API:
```bash
# Test health endpoint
curl http://localhost:8001

# Generate a tour
curl -X POST http://localhost:8001/generate-tour \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Madrid",
    "theme": "Historical",
    "duration": 120,
    "language": "en-us"
  }'
```

## Troubleshooting

1. Connection Issues:
```bash
# Check if Ollama is running
ollama list

# Verify phi4 model
ollama run phi4:latest

# Test Llama connection directly
python test_llama.py

# Check API logs
docker compose logs -f api
```

2. Common Problems:

- "Failed to connect to Llama":
  - Ensure Ollama is running
  - Check LLAMA_HOST in .env
  - Try different host values (localhost, 127.0.0.1, host.docker.internal)

- "API connection refused":
  - Ensure docker compose is running
  - Check port 8001 is not in use
  - Verify container logs

3. Debug Mode:
```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# View detailed logs
docker compose logs -f api
```

## API Endpoints

### Health Check
```bash
GET http://localhost:8001/
```

### Generate Tour
```bash
POST http://localhost:8001/generate-tour
Content-Type: application/json

{
  "city": "Madrid",
  "theme": "Historical",
  "duration": 120,
  "language": "en-us"
}
```

## Development

1. Hot Reload:
- Code changes are automatically detected
- Service restarts automatically
- No need to rebuild container

2. Monitoring:
- Metrics available at http://localhost:9090
- Response times
- Success rates
- LLM connection status

3. Logging:
- Set LOG_LEVEL=DEBUG for detailed logs
- Check logs with `docker compose logs -f api`
- Performance metrics in Prometheus format

## Environment Variables

```bash
# API Configuration
API_TITLE="Tour Generator"
API_VERSION="2.0.0"

# Llama Configuration
LLAMA_HOST=host.docker.internal
LLAMA_PORT=11434

# Service Configuration
MIN_STOPS=2
MAX_STOPS=15
MIN_DURATION=30
MAX_DURATION=240
MAX_DESCRIPTION_LENGTH=500

# Monitoring
LOG_LEVEL=DEBUG
MONITORING_PORT=9090

# API Settings
API_PORT=8001
API_HOST=0.0.0.0