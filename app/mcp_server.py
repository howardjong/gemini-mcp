#!/usr/bin/env python3
"""
Gemini MCP Server - Model Context Protocol server for Google Gemini via Vertex AI
Supports both STDIO and SSE transport for deployment flexibility
"""

import asyncio
import argparse
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import TextContent, ImageContent
import mcp.types as types

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.services.vertex_service import VertexService


# Get settings
settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Application context for shared resources"""
    vertex_service: VertexService


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    logger.info(f"Starting Gemini MCP Server with Vertex AI")
    logger.info(f"Model: {settings.VERTEX_MODEL_NAME}")
    logger.info(f"Project: {settings.GCP_PROJECT_ID}, Region: {settings.GCP_REGION}")
    
    # Initialize Vertex AI service
    vertex_service = VertexService()
    
    try:
        yield AppContext(vertex_service=vertex_service)
    finally:
        logger.info("Shutting down Gemini MCP Server")


# Create MCP server with lifespan management
mcp = FastMCP(
    "gemini-mcp",
    lifespan=app_lifespan,
    dependencies=["google-genai", "google-cloud-aiplatform"]
)


@mcp.tool()
async def chat_with_gemini(
    messages: list[dict], 
    ctx: Context,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = None,
    stream: bool = False
) -> str:
    """
    Chat with Google Gemini model through Vertex AI
    
    Args:
        messages: List of chat messages in OpenAI format
        model: Model name override (optional)
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum tokens to generate
        stream: Whether to stream the response
    """
    try:
        vertex_service = ctx.request_context.lifespan_context.vertex_service
        
        # Convert messages to MCP format
        mcp_messages = []
        for msg in messages:
            if msg["role"] == "user":
                if isinstance(msg["content"], str):
                    content = TextContent(type="text", text=msg["content"])
                else:
                    # Handle multimodal content
                    content = TextContent(type="text", text=str(msg["content"]))
                
                mcp_messages.append(types.SamplingMessage(
                    role="user",
                    content=content
                ))
            elif msg["role"] == "assistant":
                mcp_messages.append(types.SamplingMessage(
                    role="assistant", 
                    content=TextContent(type="text", text=msg["content"])
                ))
        
        # Generate response
        response = await vertex_service.generate_response(
            messages=mcp_messages,
            model=model or settings.VERTEX_MODEL_NAME,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        
        if stream:
            # For streaming, return the first chunk or full response
            async for chunk in response:
                return chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
        else:
            return response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
    except Exception as e:
        logger.error(f"Error in chat_with_gemini: {e}")
        raise


@mcp.tool()
async def get_model_info(ctx: Context) -> dict:
    """Get information about the current Gemini model"""
    return {
        "model": settings.VERTEX_MODEL_NAME,
        "project": settings.GCP_PROJECT_ID,
        "region": settings.GCP_REGION,
        "preferred_context_size": settings.PREFERRED_CONTEXT_SIZE,
        "max_context_size": settings.MAX_CONTEXT_SIZE,
        "rate_limit": f"{settings.RATE_LIMIT_RPM} requests per minute"
    }


@mcp.resource("config://model")
def get_model_config() -> str:
    """Get current model configuration as a resource"""
    config = {
        "model_name": settings.VERTEX_MODEL_NAME,
        "project_id": settings.GCP_PROJECT_ID,
        "region": settings.GCP_REGION,
        "context_sizes": {
            "preferred": settings.PREFERRED_CONTEXT_SIZE,
            "maximum": settings.MAX_CONTEXT_SIZE
        },
        "rate_limiting": {
            "rpm": settings.RATE_LIMIT_RPM
        }
    }
    return str(config)


@mcp.resource("status://health")
def get_health_status() -> str:
    """Get server health status"""
    return "Server is running and healthy"


@mcp.prompt()
def create_chat_prompt(user_message: str, system_prompt: str = None) -> list:
    """Create a chat prompt for Gemini"""
    messages = []
    
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    messages.append({
        "role": "user", 
        "content": user_message
    })
    
    return messages


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description="Gemini MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse"], 
        default="stdio",
        help="Transport type (stdio for local, sse for web deployment)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=settings.PORT,
        help="Port for SSE transport"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0", 
        help="Host for SSE transport"
    )
    
    args = parser.parse_args()
    
    if args.transport == "sse":
        # For web deployment (Render)
        logger.info(f"Starting MCP server with SSE transport on {args.host}:{args.port}")
        mcp.run_sse(host=args.host, port=args.port)
    else:
        # For local/CLI usage
        logger.info("Starting MCP server with STDIO transport")
        mcp.run()


if __name__ == "__main__":
    main()