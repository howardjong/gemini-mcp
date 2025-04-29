from typing import Dict, List, Any, AsyncGenerator, Optional
import logging
import asyncio
import os
import json
import base64

logger = logging.getLogger(__name__)

class VertexAIService:
    """Service for interacting with Google Vertex AI's Gemini models"""
    
    def __init__(self, project_id: str, region: str, model_name: str):
        """Initialize the Vertex AI service
        
        Args:
            project_id: Google Cloud project ID
            region: Google Cloud region
            model_name: Name of the Vertex AI model
        """
        self.project_id = project_id
        self.region = region
        self.model_name = model_name
        self.client = None
        self._available_models = None
        
    async def _get_client(self):
        """Get or create the google-genai Client."""
        if self.client is None:
            from google import genai
            self.client = genai.Client(vertexai=True, project=self.project_id, location=self.region)
            logger.info(f"Initialized google-genai Client for model {self.model_name}")
        return self.client
    
    async def list_models(self) -> List[str]:
        """List available models (google-genai does not support listing, so return the configured model)."""
        return [self.model_name]
    
    async def generate_content(
        self, 
        messages: List[Dict[str, Any]], 
        generation_config: Dict[str, Any] = None,
        stream: bool = True
    ) -> AsyncGenerator[Any, None]:
        """Generate content using Vertex AI's Gemini model
        
        Args:
            messages: List of message dictionaries in Vertex AI format
            generation_config: Generation parameters
            stream: Whether to stream the response
            
        Yields:
            Response chunks from the model
        """
        try:
            # Get client
            client = await self._get_client()
            
            # Create the request
            # Convert SamplingMessage or dict to serializable format for google-genai
            from google.genai import types as genai_types
            contents = []
            for msg in messages:
                # SamplingMessage (has .content)
                if hasattr(msg, 'content') and hasattr(msg.content, 'type'):
                    if msg.content.type == "text":
                        contents.append(msg.content.text)
                    elif msg.content.type == "image":
                        contents.append(genai_types.Part.from_uri(file_uri=msg.content.data, mime_type=getattr(msg.content, 'mimeType', 'image/jpeg')))
                elif isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, str):
                        contents.append(content)
                    elif isinstance(content, dict) and content.get('type') == 'image_url':
                        contents.append(genai_types.Part.from_uri(file_uri=content.get('url', ''), mime_type=content.get('mime_type', 'image/jpeg')))
            request = {
                "contents": contents,
                "generation_config": generation_config or {}
            }
            # Log request size (approximate)
            request_size = len(json.dumps(request, default=str))
            logger.info(f"Sending request to Vertex AI ({request_size} bytes)")
            # Execute in non-blocking way
            loop = asyncio.get_event_loop()
            if stream:
                # Use the correct streaming API for Gemini
                response_stream = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content_stream(
                        model=self.model_name,
                        contents=contents,
                        **(generation_config or {})
                    )
                )
                # Yield each parsed chunk (should have .text or .candidates)
                for chunk in response_stream:
                    logger.info(f"Streaming Gemini chunk: {chunk}")
                    yield chunk
            else:
                # For non-streaming, get the complete response
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        **(generation_config or {})
                    )
                )
                yield response
                
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            # Return error info
            yield {"error": str(e)}
    
    def _format_content_from_parts(self, parts: List[Dict[str, Any]]) -> str:
        """Format response content from parts structure"""
        content = ""
        for part in parts:
            if 'text' in part:
                content += part['text']
        return content
    
    def process_image_for_vertex(self, image_data_or_url: str) -> Dict[str, Any]:
        """Process image data for Vertex AI
        
        The image can be either a URL or base64 encoded data
        """
        try:
            # Check if it's a URL (starts with http)
            if image_data_or_url.startswith(('http://', 'https://')):
                import requests
                response = requests.get(image_data_or_url)
                if response.status_code == 200:
                    # Convert to base64
                    image_data = base64.b64encode(response.content).decode('utf-8')
                else:
                    raise ValueError(f"Failed to fetch image from URL: {response.status_code}")
            else:
                # Assume it's already base64 encoded
                image_data = image_data_or_url
                
            return {
                "inline_data": {
                    "mime_type": "image/jpeg",  # Assume JPEG, adjust if needed
                    "data": image_data
                }
            }
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            # Return placeholder
            return {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": ""  # Empty data
                }
            }
