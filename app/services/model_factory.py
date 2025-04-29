from typing import Dict, Type, Any
from app.services.vertex_service import VertexAIService
from app.core.config import get_settings

class ModelFactory:
    """Factory class to create appropriate model service instances"""
    
    _model_services: Dict[str, Type] = {
        "vertex-ai": VertexAIService,
        # Add more providers as they're implemented
    }
    
    @classmethod
    def get_service(cls, provider: str = "vertex-ai", **kwargs) -> Any:
        """Get the appropriate service for the provider"""
        if provider not in cls._model_services:
            raise ValueError(f"Provider {provider} not supported")
        
        settings = get_settings()
        
        # Set default values from settings if not provided
        if provider == "vertex-ai":
            kwargs.setdefault("project_id", settings.GCP_PROJECT_ID)
            kwargs.setdefault("region", settings.GCP_REGION)
            kwargs.setdefault("model_name", settings.VERTEX_MODEL_NAME)
            
        return cls._model_services[provider](**kwargs)
        
    @classmethod
    def register_service(cls, name: str, service_class: Type) -> None:
        """Register a new model service"""
        cls._model_services[name] = service_class
