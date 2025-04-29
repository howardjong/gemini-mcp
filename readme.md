# Gemini MCP Server with Vertex AI

A Model Context Protocol (MCP) server implementation for Google Gemini 2.5 Pro via Vertex AI, leveraging its 1M token context window.

## Features

- Implements the MCP server specification
- Uses the official `google-genai` Python SDK
- Connects to Google Gemini 2.5 Pro on Vertex AI
- Efficiently handles context windows with optimal parameters:
  - Preferred context size: 200,000 tokens
  - Maximum context size: 1,000,000 tokens
- Built-in rate limiting (150 requests per minute)
- Provides a well-documented HTTP API
- Containerized with Docker for easy deployment

## Step-by-Step Implementation Guide

### Prerequisites

1. Google Cloud account with Vertex AI access
2. Service account key with Vertex AI permissions
3. Python 3.8+ installed
4. Docker (optional, for containerized deployment)

### Setup

1. **Clone the project structure**:

```bash
mkdir -p gemini-mcp-server/app/{api,core,mcp,services}
mkdir -p gemini-mcp-server/credentials
cd gemini-mcp-server
```

Note: The `credentials/` directory is not tracked in the repository. You will need to create it manually.

2. **Create a virtual environment**:

```bash
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

4. **Create a service account and download key**:

Go to Google Cloud Console > IAM & Admin > Service Accounts
Create a service account with Vertex AI User and Vertex AI Publisher roles
    "model": "gemini-2.5-pro-preview-03-25",
    "messages": [
      {"role": "user", "content": "Hello, what can you do with a 1M token context window?"}
    ],
    "temperature": 0.7
  }'
API Endpoints
GET /v1/health - Health check endpoint
GET /v1/models - List available models
GET /v1/info - Get server information
POST /v1/chat/completions - Chat completion endpoint (OpenAI-compatible)
Configuration Options
The server can be configured through environment variables or the .env file:

Variable	Description	Default
GCP_PROJECT_ID	Google Cloud project ID	(required)
GCP_REGION	Google Cloud region	us-central1
GCP_SERVICE_ACCOUNT_KEY	Path to service account key file	credentials/vertex-ai-key.json
VERTEX_MODEL_NAME	Vertex AI model name	gemini-2.5-pro-preview-03-25
PORT	Server port	8000
DEBUG	Enable debug mode	false
LOG_LEVEL	Logging level	INFO
ENABLE_RATE_LIMITING	Enable rate limiting	true
RATE_LIMIT_RPM	Rate limit (requests per minute)	150
PREFERRED_CONTEXT_SIZE	Preferred context size in tokens	200000
MAX_CONTEXT_SIZE	Maximum context size in tokens	1000000
Using with LLM Clients
This server implements an OpenAI-compatible API interface, making it usable with clients that support the OpenAI API format.

Performance Considerations
Vertex AI may have its own rate limits that could be lower than our configured 150 RPM
While Gemini 2.5 Pro supports up to 1M tokens, using the preferred context size of 200K tokens will generally provide better performance
Token counting is approximate - actual token counts may vary slightly

## Implementation guide:

# Implementation Guide for Gemini MCP Server with Vertex AI

## 1. Project Setup

First, create the project structure:

```bash
mkdir -p gemini-mcp-server/app/{api,core,mcp,services}
mkdir -p gemini-mcp-server/credentials
cd gemini-mcp-server

2. Install Dependencies
Create and populate requirements.txt, then install dependencies:

Copypip install -r requirements.txt

3. Create Google Cloud Service Account
Go to the Google Cloud Console
Navigate to "IAM & Admin" > "Service Accounts"
Create a new service account with these roles:
Vertex AI User
Vertex AI Publisher
Create a key (JSON format) for this service account
Download and save it to credentials/vertex-ai-key.json

4. Configure Environment
Create a .env file in the project root:

GCP_PROJECT_ID=gen-lang-client-0597162803
GCP_REGION=us-central1
GCP_SERVICE_ACCOUNT_KEY=credentials/vertex-ai-key.json
VERTEX_MODEL_NAME=gemini-2.5-pro-preview-03-25
DEBUG=true
PORT=8000
LOG_LEVEL=INFO
ENABLE_RATE_LIMITING=true
RATE_LIMIT_RPM=150
PREFERRED_CONTEXT_SIZE=200000
MAX_CONTEXT_SIZE=1000000

5. Create All Python Files
Create all the Python files as detailed above, ensuring each file is placed in its correct directory within the project structure.

6. Run the Server
Local Development
Copy# Set environment variable to point to your service account key
export GOOGLE_APPLICATION_CREDENTIALS=credentials/vertex-ai-key.json

# Run the server
uvicorn app.main:app --reload
Docker Deployment
Copy# Build and start the container
docker-compose up -d

7. Test the Server
Test your MCP server using curl:

Copycurl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how can you help me with a 1M token context window?"}
    ],
    "temperature": 0.7
  }'

8. Connect Client Applications
You can connect any OpenAI-compatible client by pointing it to your MCP server's endpoint:

API Base URL: http://localhost:8000/v1
Troubleshooting
Authentication Issues:

Verify the service account key file is correctly placed
Ensure the service account has proper Vertex AI permissions
Model Access Issues:

Confirm your project has access to Gemini 2.5 Pro in Vertex AI
Check if the model name in configuration is correct
Rate Limit Errors:

Vertex AI may have its own rate limits that could be different from our configured limits
Adjust RATE_LIMIT_RPM if needed
Context Window Issues:

Large context sizes may require more processing time
Monitor token usage to ensure it stays within the model's capabilities

gemini-mcp-server/
├── .env
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── middlewares.py
│   │   ├── models.py
│   │   └── routes.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── errors.py
│   │   └── logging.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── protocol.py
│   └── services/
│       ├── __init__.py
│       ├── context_manager.py
│       ├── vertex_service.py
│       └── model_factory.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md