from typing import Dict, List, Any, AsyncGenerator, Optional, Union
import logging
import asyncio
import os
import json
import base64

import mcp.types as types

logger = logging.getLogger(__name__)


class VertexService:
    """MCP-compatible service for interacting with Google Vertex AI's Gemini models"""
    
    def __init__(self):
        """Initialize the Vertex AI service using environment configuration"""
        from app.core.config import get_settings
        self.settings = get_settings()
        self.client = None
        
    async def _get_client(self):
        """Get or create the google-genai Client."""
        if self.client is None:
            from google import genai
            self.client = genai.Client(
                vertexai=True, 
                project=self.settings.GCP_PROJECT_ID, 
                location=self.settings.GCP_REGION
            )
            logger.info(f"Initialized google-genai Client for model {self.settings.VERTEX_MODEL_NAME}")
        return self.client
    
    async def generate_response(
        self,
        messages: List[types.SamplingMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate response using Vertex AI Gemini model with MCP message format
        
        Args:
            messages: List of MCP SamplingMessage objects
            model: Model name override
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            OpenAI-compatible response format
        """
        try:
            client = await self._get_client()
            model_name = model or self.settings.VERTEX_MODEL_NAME
            
            # Convert MCP messages to Vertex AI format
            contents = []
            for msg in messages:
                if msg.role == "user":
                    if hasattr(msg.content, 'text'):
                        contents.append(msg.content.text)
                    elif isinstance(msg.content, types.TextContent):
                        contents.append(msg.content.text)
                    elif isinstance(msg.content, types.ImageContent):
                        # Handle image content
                        from google.genai import types as genai_types
                        contents.append(
                            genai_types.Part.from_uri(
                                file_uri=msg.content.data, 
                                mime_type=getattr(msg.content, 'mimeType', 'image/jpeg')
                            )
                        )
                elif msg.role == "assistant":
                    if hasattr(msg.content, 'text'):
                        contents.append(msg.content.text)
                    elif isinstance(msg.content, types.TextContent):
                        contents.append(msg.content.text)
            
            # Prepare generation config
            generation_config = {}
            if temperature is not None:
                generation_config["temperature"] = temperature
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            logger.info(f"Generating content with model {model_name}")
            
            loop = asyncio.get_event_loop()
            model_kwargs = {
                "model": model_name, 
                "contents": contents,
            }
            
            # Only add generation_config if we have parameters
            if generation_config:
                model_kwargs["generation_config"] = generation_config
            
            if stream:
                logger.info("Taking streaming path")
                return self._stream_response(client, model_kwargs)
            else:
                logger.info("Taking non-streaming path")
                from google.genai import types
                config = None
                if generation_config:
                    config = types.GenerateContentConfig(**generation_config)
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=model_kwargs["model"],
                        contents=model_kwargs["contents"],
                        config=config
                    )
                )
                logger.info(f"Raw response object: {type(response)}")
                formatted_response = self._format_response(response, model_name)
                logger.info(f"Formatted response content length: {len(formatted_response.get('choices', [{}])[0].get('message', {}).get('content', ''))}")
                return formatted_response
                
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return {
                "error": {
                    "message": str(e),
                    "type": "vertex_ai_error",
                    "code": "generation_failed"
                }
            }
    
    async def _stream_response(self, client, model_kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response chunks in OpenAI format"""
        try:
            # Extract generation config if present
            generation_config = model_kwargs.pop('generation_config', {})
            
            loop = asyncio.get_event_loop()
            
            # Create a function that will be called in the executor
            def generate_stream():
                from google.genai import types
                config = None
                if generation_config:
                    config = types.GenerateContentConfig(**generation_config)
                return client.models.generate_content_stream(
                    model=model_kwargs["model"],
                    contents=model_kwargs["contents"],
                    config=config
                )
                
            response_stream = await loop.run_in_executor(None, generate_stream)
            
            for chunk in response_stream:
                try:
                    # Extract text content with debug logging
                    content = self._extract_text_from_chunk(chunk)
                    logger.debug(f"Extracted content from chunk: {content}")
                    
                    # Format chunk in OpenAI-compatible format
                    yield {
                        "id": f"chatcmpl-{asyncio.current_task().get_name()}",
                        "object": "chat.completion.chunk",
                        "model": model_kwargs["model"],
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "content": content
                            },
                            "finish_reason": None
                        }]
                    }
                except Exception as e:
                    logger.error(f"Error processing chunk: {str(e)}")
                    logger.error(f"Chunk type: {type(chunk)}")
                    logger.error(f"Chunk content: {chunk}")
                    raise
            
            # Send final chunk with finish_reason
            yield {
                "id": f"chatcmpl-{asyncio.current_task().get_name()}",
                "object": "chat.completion.chunk", 
                "model": model_kwargs["model"],
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            
        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}")
            yield {
                "error": {
                    "message": str(e),
                    "type": "stream_error"
                }
            }
    
    def _format_response(self, response, model_name: str) -> Dict[str, Any]:
        """Format Vertex AI response to OpenAI-compatible format"""
        try:
            content = self._extract_text_from_response(response)
            
            return {
                "id": f"chatcmpl-{id(response)}",
                "object": "chat.completion",
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,  # Vertex doesn't provide token counts
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}")
            return {
                "error": {
                    "message": f"Failed to format response: {str(e)}",
                    "type": "format_error"
                }
            }
    
    def _extract_text_from_response(self, response) -> str:
        """Extract text content from Vertex AI response"""
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    parts = candidate.content.parts
                    text_parts = []
                    for part in parts:
                        if hasattr(part, 'text'):
                            text_parts.append(part.text)
                    return ''.join(text_parts)
            
            # Fallback: try to convert response to string
            return str(response)
            
        except Exception as e:
            logger.error(f"Error extracting text from response: {str(e)}")
            return f"Error processing response: {str(e)}"
    
    def _extract_text_from_chunk(self, chunk) -> str:
        """Extract text content from streaming chunk"""
        try:
            # Try to access the text directly first (newer SDK versions)
            if hasattr(chunk, 'text'):
                return chunk.text or ""
                
            # Fallback to candidates structure (older SDK versions)
            if hasattr(chunk, 'candidates') and chunk.candidates:
                candidate = chunk.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    parts = candidate.content.parts
                    text_parts = []
                    for part in parts:
                        if hasattr(part, 'text'):
                            text_parts.append(part.text)
                    return ''.join(text_parts)
                elif hasattr(candidate, 'content') and hasattr(candidate.content, 'text'):
                    return candidate.content.text or ""
            
            # Try to get text from chunk directly as a string
            if isinstance(chunk, str):
                return chunk
                
            # Debug logging for unexpected chunk format
            logger.warning(f"Unexpected chunk format: {chunk}")
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting text from chunk: {str(e)}")
            return ""
    

    async def list_available_models(self) -> List[str]:
        """List available models"""
        return [self.settings.VERTEX_MODEL_NAME]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        return {
            "model": self.settings.VERTEX_MODEL_NAME,
            "project": self.settings.GCP_PROJECT_ID,
            "region": self.settings.GCP_REGION,
            "context_window": {
                "preferred": self.settings.PREFERRED_CONTEXT_SIZE,
                "maximum": self.settings.MAX_CONTEXT_SIZE
            }
        }