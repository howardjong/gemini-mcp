from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import logging
import uuid
import time
from typing import Dict, Any, List, Optional

from app.api.models import MCPRequest, ModelInfoResponse, ErrorResponse
from app.core.config import get_settings
from app.mcp.protocol import GeminiMCPHandler
from app.services.vertex_service import VertexAIService
from app.core.rate_limiter import RateLimiter

router = APIRouter(prefix="/v1")
logger = logging.getLogger(__name__)

# Dependency injection
async def get_vertex_service() -> VertexAIService:
    settings = get_settings()
    return VertexAIService(
        project_id=settings.GCP_PROJECT_ID,
        region=settings.GCP_REGION,
        model_name=settings.VERTEX_MODEL_NAME
    )

async def get_mcp_handler(
    vertex_service: VertexAIService = Depends(get_vertex_service)
) -> GeminiMCPHandler:
    return GeminiMCPHandler(model_service=vertex_service)

@router.get("/models", response_model=List[ModelInfoResponse])
async def list_models(vertex_service: VertexAIService = Depends(get_vertex_service)):
    """List available models"""
    try:
        models = await vertex_service.list_models()
        return [
            ModelInfoResponse(
                id=model,
                object="model",
                created=int(time.time()),
                owned_by="google"
            ) for model in models
        ]
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")

@router.get("/info")
async def server_info():
    """Get server information and capabilities"""
    settings = get_settings()
    return {
        "server": "gemini-mcp-server",
        "version": "0.1.0",
        "vertex_ai": {
            "project_id": settings.GCP_PROJECT_ID,
            "region": settings.GCP_REGION,
            "model": settings.VERTEX_MODEL_NAME
        },
        "max_context_size": settings.MAX_CONTEXT_SIZE,
        "preferred_context_size": settings.PREFERRED_CONTEXT_SIZE,
        "capabilities": ["text", "vision", "streaming"],
        "protocol_version": "mcp-v1"
    }

@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    mcp_handler: GeminiMCPHandler = Depends(get_mcp_handler)
):
    """Handle chat completions with MCP"""
    try:
        # Parse request body
        body = await request.json()
        # Convert to MCP Request format
        mcp_request = await _convert_to_mcp_request(body)
        # Handle streaming vs non-streaming
        stream = body.get("stream", False)
        if stream:
            # Return streaming response
            return StreamingResponse(
                _stream_mcp_response(mcp_handler, mcp_request),
                media_type="text/event-stream"
            )
        else:
            # Return complete response
            response = await _get_complete_response(mcp_handler, mcp_request)
            return response
    except Exception as e:
        logger.error(f"Error in chat completions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.post("/models/{model_id}/chat")
async def chat_completions_model(
    model_id: str,
    request: Request,
    mcp_handler: GeminiMCPHandler = Depends(get_mcp_handler)
):
    """Handle chat completions with MCP (model in path)"""
    try:
        # Parse request body
        body = await request.json()
        # Inject model_id from path into the body, overriding if present
        body["model"] = model_id
        mcp_request = await _convert_to_mcp_request(body)
        stream = body.get("stream", False)
        if stream:
            return StreamingResponse(
                _stream_mcp_response(mcp_handler, mcp_request),
                media_type="text/event-stream"
            )
        else:
            response = await _get_complete_response(mcp_handler, mcp_request)
            return response
    except Exception as e:
        logger.error(f"Error in chat completions (model in path): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

    """Handle chat completions with MCP"""
    try:
        # Parse request body
        body = await request.json()
        
        # Convert to MCP Request format
        mcp_request = await _convert_to_mcp_request(body)
        
        # Handle streaming vs non-streaming
        stream = body.get("stream", False)
        
        if stream:
            # Return streaming response
            return StreamingResponse(
                _stream_mcp_response(mcp_handler, mcp_request),
                media_type="text/event-stream"
            )
        else:
            # Return complete response
            response = await _get_complete_response(mcp_handler, mcp_request)
            return response
            
    except Exception as e:
        logger.error(f"Error in chat completions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

async def _convert_to_mcp_request(body: Dict[str, Any]):
    """For the new MCP SDK, just return the request body as-is (dict)."""
    return body


async def _stream_mcp_response(mcp_handler, mcp_request):
    """Stream responses from MCP handler (dict-based)."""
    try:
        async for response in mcp_handler.handle_request(mcp_request):
            if 'error' in response:
                yield f"data: {json.dumps({'error': response['error']})}\n\n"
                return
            if 'message' in response:
                yield f"data: {json.dumps({'message': response['message']})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error in streaming response: {str(e)}")
        yield f"data: {json.dumps({'error': {'type': 'server_error', 'message': str(e)}})}\n\n"

async def _get_complete_response(mcp_handler, mcp_request):
    """Get complete (non-streaming) response from MCP handler (dict-based)."""
    response_content = ""
    error = None
    try:
        async for chunk in mcp_handler.handle_request(mcp_request):
            if 'error' in chunk:
                error = chunk['error']
                break
            if 'message' in chunk and 'content' in chunk['message']:
                response_content += chunk['message']['content']
        if error:
            return {"error": error}
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": mcp_request.get('model', 'unknown'),
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "index": 0,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(str(mcp_request.get('messages', []))) // 4,
                "completion_tokens": len(response_content) // 4,
                "total_tokens": (len(str(mcp_request.get('messages', []))) + len(response_content)) // 4
            }
        }
    except Exception as e:
        logger.error(f"Error getting complete response: {str(e)}")
        return {"error": {"type": "server_error", "message": str(e)}}
