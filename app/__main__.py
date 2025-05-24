#!/usr/bin/env python3
"""
Entry point for the Gemini MCP Server module
Allows running with: python -m app
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.core.config import get_settings
    
    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)