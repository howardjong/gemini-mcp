from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import time
import uuid

class ModelInfoResponse(BaseModel):
    """Model information response"""
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "google"

class MCPRequest(BaseModel):
    """MCP Request model"""
    model: str
    messages: List[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]] = None
    stream: Optional[bool] = False

class MCPResponse(BaseModel):
    """MCP Response model"""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4()}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

class ErrorResponse(BaseModel):
    """Error response model"""
    error: Dict[str, Any]
