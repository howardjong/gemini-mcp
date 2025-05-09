from mcp.types import Role, SamplingMessage, TextContent, ImageContent
from typing import List, Optional, Dict, Any, AsyncGenerator
import logging
import json

from app.services.vertex_service import VertexAIService
from app.core.errors import MCPError

logger = logging.getLogger(__name__)

class GeminiMCPHandler:
    def __init__(self, model_service: VertexAIService):
        self.model_service = model_service
    
    async def handle_request(self, request: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process MCP request and generate responses (streaming). Supports Google Search grounding via 'grounding' or 'tools' in the request."""
        try:
            logger.info(f"Processing MCP request for model: {request.get('model')}")

            # Convert API messages to SamplingMessage list
            mcp_messages = self._convert_to_sampling_messages(request.get('messages', []))
            generation_config = self._extract_generation_config(request.get('parameters', {}))

            # Determine tools for grounding
            tools = None
            # Prefer tools param if provided
            if 'tools' in request and isinstance(request['tools'], list):
                tools = request['tools']
            elif request.get('grounding') == 'google_search':
                tools = [{"tool": "google_search"}]

            # Get response from Vertex AI
            async for chunk in self.model_service.generate_content(
                messages=mcp_messages,
                generation_config=generation_config,
                stream=True,
                tools=tools
            ):
                # Convert Vertex AI response to OpenAI/MCP-like dict
                mcp_response = self._convert_to_mcp_response(chunk)
                yield mcp_response
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
        # This should be adapted to your OpenAI/MCP-compatible output format
        try:
            if hasattr(vertex_chunk, 'error') or (isinstance(vertex_chunk, dict) and 'error' in vertex_chunk):
                error_msg = str(vertex_chunk.get('error', 'Unknown error')) if isinstance(vertex_chunk, dict) else str(vertex_chunk.error)
                return {"error": {"type": "model_error", "message": error_msg}}
            # Assume text chunk
            text_content = vertex_chunk.get('text') if isinstance(vertex_chunk, dict) else str(vertex_chunk)
            return {
                "message": {
                    "role": "assistant",
                    "content": text_content
                }
            }
        except Exception as e:
            logger.error(f"Error converting Vertex AI response: {str(e)}")
            return {"error": {"type": "conversion_error", "message": str(e)}}

    

    
    def _get_image_data(self, image_url: str) -> str:
        """Get base64 encoded image data from URL"""
        # In a real implementation, this would fetch and encode the image
        # For this example, we'll just return a placeholder
        import base64
        try:
            import requests
            response = requests.get(image_url)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode('utf-8')
        except:
            pass
            
        # Return a placeholder if fetching fails
        logger.warning(f"Could not fetch image from {image_url}, using placeholder")
        return "placeholder_base64_data"
    
    def _extract_generation_config(self, parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract and convert generation parameters for Vertex AI"""
        if not parameters:
            return {}
            
        generation_config = {}
        
        # Map MCP parameters to Vertex AI parameters
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
            # Error handling
            if hasattr(vertex_chunk, 'error') or (isinstance(vertex_chunk, dict) and 'error' in vertex_chunk):
                error_msg = str(vertex_chunk.get('error', 'Unknown error')) if isinstance(vertex_chunk, dict) else str(vertex_chunk.error)
                return {"error": {"type": "model_error", "message": error_msg}}
            # Extract text content from various Vertex AI response formats
            text_content = ""
            if hasattr(vertex_chunk, 'text'):
                text_content = vertex_chunk.text
            elif isinstance(vertex_chunk, dict) and 'candidates' in vertex_chunk:
                for candidate in vertex_chunk['candidates']:
                    if 'content' in candidate:
                        content = candidate['content']
                        if isinstance(content, dict) and 'parts' in content:
                            for part in content['parts']:
                                if 'text' in part:
                                    text_content += part['text']
            elif isinstance(vertex_chunk, dict) and 'text' in vertex_chunk:
                text_content = vertex_chunk['text']
            return {
                "message": {
                    "role": "assistant",
                    "content": text_content
                }
            }
        except Exception as e:
            logger.error(f"Error converting Vertex AI response: {str(e)}")
            return {"error": {"type": "conversion_error", "message": str(e)}}
