from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

class MCPError(BaseModel):
    """Standardized MCP error format"""
    type: str
    message: str
    param: Optional[str] = None
    code: Optional[str] = None
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary, removing None values"""
        return {k: v for k, v in super().dict().items() if v is not None}

# Define common errors
class ModelNotFoundError(MCPError):
    def __init__(self, model: str):
        super().__init__(
            type="model_not_found",
            message=f"Model '{model}' not found",
            code="model_not_found"
        )

class InvalidRequestError(MCPError):
    def __init__(self, message: str, param: Optional[str] = None):
        super().__init__(
            type="invalid_request",
            message=message,
            param=param,
            code="invalid_request"
        )

class AuthenticationError(MCPError):
    def __init__(self):
        super().__init__(
            type="authentication_error",
            message="Invalid API key or not authorized for this model",
            code="authentication_error"
        )

class RateLimitError(MCPError):
    def __init__(self):
        super().__init__(
            type="rate_limit_exceeded",
            message="Rate limit exceeded",
            code="rate_limit"
        )

class ServerError(MCPError):
    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            type="server_error",
            message=message,
            code="server_error"
        )
