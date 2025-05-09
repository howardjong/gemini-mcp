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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"VertexAIService: Initialized with model_name={model_name}")
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
        stream: bool = True,
        tools: Optional[list] = None
    ) -> AsyncGenerator[Any, None]:
        """Generate content using Vertex AI's Gemini model, with optional Google Search grounding.

        Args:
            messages: List of message dictionaries in Vertex AI format
            generation_config: Generation parameters
            stream: Whether to stream the response
            tools: Optional list of tools (e.g., [{"tool": "google_search"}])

        Yields:
            Response chunks from the model
        """
        try:
            # Helper for REST API fallback
            def vertex_rest_generate_content(project_id, region, model_name, messages, generation_config=None, tools=None):
                import requests
                from google.auth.transport.requests import Request as GoogleAuthRequest
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                credentials.refresh(GoogleAuthRequest())
                access_token = credentials.token
                endpoint = (
                    f"https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/publishers/google/models/{model_name}:generateContent"
                )
                # Format messages for REST API
                contents = []
                for msg in messages:
                    # Accept both dicts and objects with .role/.content
                    role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "user")
                    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                    if content and isinstance(content, str):
                        contents.append({"role": role or "user", "parts": [{"text": content}]})
                body = {"contents": contents}
                if generation_config:
                    body["generationConfig"] = generation_config
                if tools:
                    body["tools"] = [{"googleSearch": {}}]
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }
                logger.info(f"Vertex REST API request body: {json.dumps(body, indent=2)}")
                response = requests.post(endpoint, headers=headers, json=body)
                if not response.ok:
                    logger.error(f"Vertex REST API error: {response.status_code} {response.text}")
                    # Optionally, return the error as a dict for the API response
                    return {"error": response.text, "status_code": response.status_code}
                return response.json()

            # If tools include google_search, use REST API fallback
            if tools and any(t.get("tool") == "google_search" for t in tools):
                logger.info("Using REST API for Google Search grounding.")
                logger.info(f"Messages passed to REST helper: {messages}")
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: vertex_rest_generate_content(
                        self.project_id,
                        self.region,
                        self.model_name,
                        messages,
                        generation_config=generation_config,
                        tools=tools,
                    )
                )
                yield response
                return

            # Otherwise, use SDK as before
            client = await self._get_client()
            from google.genai import types as genai_types
            contents = []
            for msg in messages:
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
            # Log request size (approximate)
            request_size = len(json.dumps(contents, default=str))
            logger.info(f"Sending request to Vertex AI ({request_size} bytes)")
            loop = asyncio.get_event_loop()
            model_kwargs = dict(model=self.model_name, contents=contents, **(generation_config or {}))
            if stream:
                response_stream = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content_stream(
                        **model_kwargs
                    )
                )
                for chunk in response_stream:
                    logger.info(f"Streaming Gemini chunk: {chunk}")
                    yield chunk
            else:
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        **model_kwargs
                    )
                )
                yield response
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
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
