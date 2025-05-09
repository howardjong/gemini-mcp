# Gemini MCP Server

A FastAPI-based Model Control Protocol (MCP) server for Google's Gemini models on Vertex AI, with OpenAI-compatible endpoints.

## Features
- Streaming responses
- Rate limiting (150 RPM default)
- Vertex AI integration
- Health checks (`/v1/health`)

## Prerequisites
- Python 3.9+
- Google Cloud account with:
  - Vertex AI API enabled
  - Service account with `Vertex AI User` and `Service Account Token Creator` roles

## Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/howardjong/gemini-mcp.git
   cd gemini-mcp
   ```

2. **Create a service account key**
   - Navigate to [GCP IAM](https://console.cloud.google.com/iam-admin/serviceaccounts)
   - Create a key (JSON) for your service account
   - Save to `credentials/vertex-ai-key.json`

3. **Configure environment**
   Create `.env` in the project root:
   ```env
   # Required
   GCP_PROJECT_ID=your-project-id  # From GCP Console
   GCP_REGION=us-central1
   GCP_SERVICE_ACCOUNT_KEY=credentials/vertex-ai-key.json
   VERTEX_MODEL_NAME=gemini-2.5-pro-preview-05-06
   
   # Optional
   DEBUG=false
   PORT=8000
   LOG_LEVEL=INFO
   ENABLE_RATE_LIMITING=true
   RATE_LIMIT_RPM=150
   ```

## Running the Server
```bash
# Install dependencies
pip install -r requirements.txt

# Development (auto-reload)
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --port 8000 --workers 4
```

## API Documentation
- Interactive docs: `http://localhost:8000/docs`
- Example request:
  ```bash
  curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello!"}]}'
  ```

## Deployment
### Render/Cloud Run
- Set `PORT` env var
- Enable HTTPS

## Security
 **Never commit sensitive files**:
```.gitignore
.env
credentials/
```

## License
MIT