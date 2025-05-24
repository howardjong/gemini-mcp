from mcp.types import Role, SamplingMessage, TextContent, ImageContent
from typing import List, Optional, Dict, Any, AsyncGenerator
import logging
import json

from app.services.vertex_service import VertexService as VertexAIService
from app.core.errors import MCPError

logger = logging.getLogger(__name__)

class GeminiMCPHandler:
    def __init__(self, model_service: VertexAIService):
        self.model_service = model_service
    
    async def handle_request(self, request: Dict[str, Any], stream: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """Process MCP request and generate responses."""
        try:
            logger.info(f"Processing MCP request for model: {request.get('model')}")

            # Convert API messages to SamplingMessage list
            mcp_messages = self._convert_to_sampling_messages(request.get('messages', []))
            generation_config = self._extract_generation_config(request.get('parameters', {}))

            # Get response from Vertex AI
            response = await self.model_service.generate_response(
                messages=mcp_messages,
                model=request.get('model'),
                temperature=generation_config.get('temperature', 0.7),
                max_tokens=generation_config.get('max_tokens'),
                stream=stream
            )

            # If response is an async generator, yield from it
            if hasattr(response, '__aiter__'):
                logger.info("Processing streaming response")
                async for chunk in response:
                    yield self._convert_to_mcp_response(chunk)
            else:
                # For non-streaming, return the complete response directly
                logger.info(f"Processing non-streaming response: {type(response)}")
                logger.info(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'not a dict'}")
                if isinstance(response, dict) and 'error' in response:
                    # Handle error responses
                    yield {"error": response['error']}
                elif isinstance(response, dict) and 'choices' in response:
                    # For complete OpenAI-format responses, extract the content and yield it
                    logger.info(f"Choices content: {response['choices']}")
                    try:
                        content = response['choices'][0]['message']['content']
                        yield {
                            "message": {
                                "role": "assistant", 
                                "content": content
                            }
                        }
                        logger.info(f"Successfully extracted content: {content[:100]}...")
                    except (KeyError, IndexError) as e:
                        logger.error(f"Failed to extract content from response: {e}")
                        yield {"error": {"type": "format_error", "message": f"Failed to extract content: {e}"}}
                else:
                    # Fallback to conversion
                    converted = self._convert_to_mcp_response(response)
                    logger.info(f"Converted response: {converted}")
                    yield converted
                
        except Exception as e:
            logger.error(f"Error processing MCP request: {str(e)}")
            yield {"error": {"type": "server_error", "message": str(e)}}

    def _convert_to_sampling_messages(self, messages: List[Dict[str, Any]]) -> List[SamplingMessage]:
        """Convert API messages to MCP SamplingMessage format."""
        result = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")
            # Only supporting text and image for now
            if isinstance(content, str):
                result.append(SamplingMessage(
                    role=role,
                    content=TextContent(type="text", text=content)
                ))
            elif isinstance(content, list):
                # Multimodal content
                for part in content:
                    if isinstance(part, str):
                        result.append(SamplingMessage(
                            role=role,
                            content=TextContent(type="text", text=part)
                        ))
                    elif isinstance(part, dict):
                        if part.get("type") == "text":
                            result.append(SamplingMessage(
                                role=role,
                                content=TextContent(type="text", text=part.get("text", ""))
                            ))
                        elif part.get("type") == "image_url":
                            image_url = part.get("image_url", {}).get("url", "")
                            # Placeholder: you may want to fetch and encode image data
                            result.append(SamplingMessage(
                                role=role,
                                content=ImageContent(type="image", data=image_url, mimeType="image/jpeg")
                            ))
            else:
                # Unknown content type
                continue
        return result

    def _extract_generation_config(self, parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract and convert generation parameters for Vertex AI."""
        if not parameters:
            return {}
        generation_config = {}
        if "temperature" in parameters:
            generation_config["temperature"] = parameters["temperature"]
        if "top_p" in parameters:
            generation_config["top_p"] = parameters["top_p"]
        if "max_tokens" in parameters:
            generation_config["max_output_tokens"] = parameters["max_tokens"]
        if "stop" in parameters:
            generation_config["stop_sequences"] = parameters["stop"]
        return generation_config


    def _convert_to_mcp_response(self, vertex_chunk: Any) -> Dict[str, Any]:
        """Convert Vertex AI response chunk to MCP-like response dict."""
        try:
            # Handle OpenAI-formatted chunks (which is what our Vertex service returns)
            if isinstance(vertex_chunk, dict):
                # If it's already an OpenAI-formatted chunk, extract the content
                if 'choices' in vertex_chunk:
                    choices = vertex_chunk['choices']
                    if choices and len(choices) > 0:
                        choice = choices[0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            content = choice['delta']['content']
                            return {
                                "message": {
                                    "role": "assistant",
                                    "content": content
                                }
                            }
                        elif 'message' in choice and 'content' in choice['message']:
                            content = choice['message']['content']
                            return {
                                "message": {
                                    "role": "assistant",
                                    "content": content
                                }
                            }
                
                # Handle error responses
                if 'error' in vertex_chunk:
                    error_msg = str(vertex_chunk['error'])
                    return {"error": {"type": "model_error", "message": error_msg}}
                
                # Handle direct text content
                if 'text' in vertex_chunk:
                    return {
                        "message": {
                            "role": "assistant",
                            "content": vertex_chunk['text']
                        }
                    }
                
                # Handle raw Vertex AI response format (fallback)
                if 'candidates' in vertex_chunk:
                    text_content = ""
                    for candidate in vertex_chunk['candidates']:
                        if 'content' in candidate:
                            content = candidate['content']
                            if isinstance(content, dict) and 'parts' in content:
                                for part in content['parts']:
                                    if 'text' in part:
                                        text_content += part['text']
                    return {
                        "message": {
                            "role": "assistant",
                            "content": text_content
                        }
                    }
            
            # Handle direct text responses
            if hasattr(vertex_chunk, 'text'):
                return {
                    "message": {
                        "role": "assistant",
                        "content": vertex_chunk.text
                    }
                }
            
            # If we can't parse it, return empty content
            logger.warning(f"Unable to parse chunk format: {type(vertex_chunk)}, content: {vertex_chunk}")
            return {
                "message": {
                    "role": "assistant",
                    "content": ""
                }
            }
            
        except Exception as e:
            logger.error(f"Error converting Vertex AI response: {str(e)}")
            return {"error": {"type": "conversion_error", "message": str(e)}}
