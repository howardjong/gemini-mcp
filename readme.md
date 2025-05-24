# Gemini API Server

A **REST API server** providing OpenAI-compatible chat completions for Google's Gemini models via Vertex AI. Built with FastAPI for high performance and easy deployment.

## Features

- **OpenAI Compatible**: Drop-in replacement for OpenAI chat completions API
- **FastAPI**: High-performance async API with automatic docs
- **Gemini Integration**: Latest Gemini 2.5 Pro via Vertex AI  
- **Rate Limiting**: Built-in request rate limiting
- **Streaming**: Real-time response streaming support
- **Docker Ready**: Production-ready containerization
- **Auto Docs**: Interactive API documentation at `/docs`

## Architecture

This server provides a REST API with OpenAI-compatible endpoints:
- **Framework**: FastAPI with async/await support
- **Transport**: HTTP/REST with JSON payloads
- **Endpoints**: `/v1/chat/completions`, `/v1/models`, `/v1/health`
- **Compatibility**: OpenAI Python client and other OpenAI-compatible tools

## Prerequisites

- Python 3.10+
- Google Cloud account with:
  - Vertex AI API enabled
  - Service account with `Vertex AI User` role

## Setup

### 1. Clone and Install
```bash
git clone https://github.com/howardjong/gemini-mcp.git
cd gemini-mcp
pip install -r requirements.txt
```

### 2. Google Cloud Setup
Create a service account key:
- Navigate to [GCP IAM](https://console.cloud.google.com/iam-admin/serviceaccounts)
- Create a service account with `Vertex AI User` role
- Generate JSON key and save to `credentials/vertex-ai-key.json`

### 3. Environment Configuration
Create `.env` file:
```env
# Required
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_SERVICE_ACCOUNT_KEY=credentials/vertex-ai-key.json
VERTEX_MODEL_NAME=gemini-2.5-pro-preview-05-06

# Optional
DEBUG=false
PORT=8000
LOG_LEVEL=INFO
RATE_LIMIT_RPM=150
```

## Usage

### Local Development 
```bash
# Run FastAPI server for local development
python -m app.main

# Or using the module entry point
python -m app
```

### Web Deployment
```bash
# For production deployment (Docker)
docker build -t gemini-mcp .
docker run -p 8000:8000 --env-file .env gemini-mcp

# Or run directly with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Deploy to Render

1. **Connect your GitHub repository** to Render
2. **Set environment variables** in Render dashboard:
   ```
   GCP_PROJECT_ID=your-project-id
   GCP_REGION=us-central1
   VERTEX_MODEL_NAME=gemini-2.5-pro-preview-05-06
   ```
3. **Upload service account key** content as `GCP_SERVICE_ACCOUNT_KEY_JSON` environment variable
4. **Deploy** - Render will automatically build and run the FastAPI server

The deployed server will be accessible as a REST API with OpenAI-compatible chat completions endpoint.

## API Endpoints

### Chat Completions
- `POST /v1/chat/completions` - OpenAI-compatible chat completions
- `POST /v1/models/{model_id}/chat` - Chat with specific model

### Model Information  
- `GET /v1/models` - List available models
- `GET /v1/info` - Server and model information

### Health Check
- `GET /v1/health` - Server health status

## API Usage

### Python Client Example
```python
import requests

# Chat with Gemini
response = requests.post("https://your-app.onrender.com/v1/chat/completions", 
    json={
        "model": "gemini-2.5-pro-preview-05-06",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "stream": false
    }
)

print(response.json())
```

### cURL Example
```bash
curl -X POST https://your-app.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro-preview-05-06", 
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Streaming Example
```bash
# Stream responses in real-time
curl -X POST https://your-app.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro-preview-05-06",
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ],
    "stream": true
  }'
```

```python
# Python streaming example
import requests

response = requests.post("https://your-app.onrender.com/v1/chat/completions",
    json={
        "model": "gemini-2.5-pro-preview-05-06",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

## Troubleshooting

### Common Issues

- **Rate Limiting**: If you encounter rate limiting errors, check your `RATE_LIMIT_RPM` environment variable and adjust as needed.
- **Model Not Found**: Ensure that the `VERTEX_MODEL_NAME` environment variable is set correctly and that the model exists in your Vertex AI project.
- **Authentication Errors**: Verify that your service account key is correctly configured and that the `GCP_SERVICE_ACCOUNT_KEY` environment variable is set.

### Debugging

- **Enable Debug Mode**: Set `DEBUG=true` in your `.env` file to enable debug logging.
- **Check Server Logs**: Inspect server logs for error messages and stack traces.

## OpenAI Compatibility

This server provides OpenAI-compatible endpoints, making it a drop-in replacement for OpenAI's API when using Gemini models via Vertex AI.

## Development

### Testing
```bash
# Run tests
pytest

# Test API server locally
python -m app.main
```

### Docker Development
```bash
# Build and run
docker build -t gemini-mcp .
docker run -p 8000:8000 --env-file .env gemini-mcp
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following MCP standards
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- [MCP Documentation](https://modelcontextprotocol.io)
- [Report Issues](https://github.com/howardjong/gemini-mcp/issues)
- [Discussions](https://github.com/howardjong/gemini-mcp/discussions)